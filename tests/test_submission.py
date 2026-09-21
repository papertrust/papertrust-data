import io
import unittest
from unittest.mock import patch

from scripts.submission import (
    SubmissionError,
    build_record,
    fetch_arxiv_metadata,
    parse_fields,
    parse_issue,
)


def reproduction_issue(summary: str, *, doi: str = "", version: str = "latest"):
    return {
        "title": "[Reproduction] arXiv:9913.99999",
        "body": f"""### arXiv ID

9913.99999

### Paper version

{version}

### Result

not_reproduced

### Tags

performance_mismatch, independent_reproduction

### Summary

{summary}

### Evidence DOI

{doi}
""",
    }


class SubmissionTests(unittest.TestCase):
    def test_markdown_summary_and_optional_doi(self):
        issue = reproduction_issue(
            "The **reported result** was not reproduced. See [notes](https://example.org/notes)."
        )
        submission = parse_issue(issue)
        self.assertIsNone(submission.evidence_doi)
        self.assertEqual(submission.paper_version, "latest")

    def test_shell_syntax_is_plain_text(self):
        marker = "$(touch /tmp/papertrust-injection)"
        submission = parse_issue(reproduction_issue(f"Literal shell-looking text stays plain text: {marker}."))
        self.assertIn(marker, submission.summary)

    def test_reserved_heading_injection_is_rejected(self):
        issue = reproduction_issue(
            "A valid-looking summary with a reserved heading.\n\n### Evidence DOI\n\n10.9999/attacker"
        )
        with self.assertRaisesRegex(SubmissionError, "duplicate reserved heading"):
            parse_issue(issue)

    def test_raw_html_is_rejected(self):
        with self.assertRaisesRegex(SubmissionError, "raw HTML"):
            parse_issue(reproduction_issue("This contains enough text but also <script>alert(1)</script>."))

    def test_dangerous_markdown_url_is_rejected(self):
        with self.assertRaisesRegex(SubmissionError, "dangerous URL scheme"):
            parse_issue(reproduction_issue("This is long enough and links to [x](javascript:alert(1))."))

    def test_markdown_images_are_rejected(self):
        with self.assertRaisesRegex(SubmissionError, "Markdown images"):
            parse_issue(reproduction_issue("This is long enough and embeds ![tracking](https://evil.invalid/a.png)."))

    def test_non_http_markdown_links_are_rejected(self):
        with self.assertRaisesRegex(SubmissionError, "HTTP"):
            parse_issue(reproduction_issue("This is long enough and links to [local data](file:///etc/passwd)."))

    def test_fetch_arxiv_metadata_uses_exact_version(self):
        page = b"""<!doctype html>
<html><head>
<meta name="citation_title" content="  A Synthetic Paper Title  ">
<meta name="citation_author" content="Ada Example">
<meta name="citation_author" content="Lin Example">
<meta name="citation_abstract" content="A synthetic abstract used only for automated testing.">
</head></html>
"""
        with patch("scripts.submission.urllib.request.urlopen", return_value=io.BytesIO(page)) as mocked:
            metadata = fetch_arxiv_metadata("9913.99999", "v3")

        requested_url = mocked.call_args.args[0].full_url
        self.assertEqual(requested_url, "https://arxiv.org/abs/9913.99999v3")
        self.assertEqual(metadata.title, "A Synthetic Paper Title")
        self.assertEqual(metadata.authors, ("Ada Example", "Lin Example"))
        self.assertEqual(metadata.abstract, "A synthetic abstract used only for automated testing.")
        self.assertEqual(metadata.pdf_url, "https://arxiv.org/pdf/9913.99999v3")

    def test_latest_version_accepts_submission_history_markers(self):
        page = b"""<!doctype html><div class="submission-history">
[v1] synthetic first version
[v2] synthetic revision
[v5] synthetic latest revision
</div>"""
        with patch("scripts.submission.urllib.request.urlopen", return_value=io.BytesIO(page)):
            from scripts.submission import latest_arxiv_version

            self.assertEqual(latest_arxiv_version("9913.99999"), "v5")

    def test_build_record_resolves_latest_and_omits_evidence(self):
        submission = parse_issue(reproduction_issue("A sufficiently detailed reproduction summary for testing."))
        with patch("scripts.submission.latest_arxiv_version", return_value="v4"):
            record = build_record(submission)
        self.assertEqual(record["paper_version"], "v4")
        self.assertNotIn("evidence", record)

    def test_explicit_nonexistent_version_is_rejected(self):
        submission = parse_issue(
            reproduction_issue("A sufficiently detailed reproduction summary for testing.", version="v9")
        )
        with patch("scripts.submission.latest_arxiv_version", return_value="v4"):
            with self.assertRaisesRegex(SubmissionError, "does not exist"):
                build_record(submission)

    def test_parser_allows_non_reserved_markdown_heading(self):
        fields = parse_fields(
            """### Summary

Main text.

#### Details

Still summary content.

### Evidence DOI

"""
        )
        self.assertIn("#### Details", fields["Summary"])


if __name__ == "__main__":
    unittest.main()
