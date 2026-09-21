from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

ARXIV_ID_RE = re.compile(r"(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+/[0-9]{7})")
VERSION_RE = re.compile(r"v([1-9][0-9]*)")
DOI_RE = re.compile(r"10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
RAW_HTML_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^>]*)?>|<!--", re.IGNORECASE)
DANGEROUS_SCHEME_RE = re.compile(r"(?i)(?:javascript|vbscript|data)\s*:")
IMAGE_MARKDOWN_RE = re.compile(r"!\[")
MARKDOWN_LINK_RE = re.compile(r"""\[[^\]]*\]\(([^)\s]+)(?:\s+["'][^)]*["'])?\)""")

ALLOWED_RESULTS = {
    "reproduced",
    "partially_reproduced",
    "not_reproduced",
    "inconclusive",
}

ALLOWED_TAGS = {
    "artifact_missing",
    "artifact_broken",
    "artifact_incomplete",
    "checkpoint_missing",
    "training_code_missing",
    "evaluation_code_missing",
    "raw_results_missing",
    "benchmark_mismatch",
    "metric_mismatch",
    "performance_mismatch",
    "training_mismatch",
    "documentation_incomplete",
    "undocumented_configuration",
    "version_mismatch",
    "independent_reproduction",
    "author_reproduction",
    "corrected",
    "resolved",
    "disputed",
}

KNOWN_HEADINGS = (
    "arXiv ID",
    "Paper version",
    "Result",
    "Tags",
    "Summary",
    "Evidence DOI",
)
HEADING_RE = re.compile(
    r"^### (" + "|".join(re.escape(h) for h in KNOWN_HEADINGS) + r")\s*$",
    re.MULTILINE,
)
EMPTY_RESPONSES = {"", "_No response_", "No response"}


class SubmissionError(ValueError):
    pass


@dataclass(frozen=True)
class Submission:
    kind: str
    arxiv_id: str
    paper_version: str
    tags: tuple[str, ...]
    summary: str
    evidence_doi: str | None
    result: str | None = None


@dataclass(frozen=True)
class ArxivMetadata:
    title: str
    authors: tuple[str, ...]
    abstract: str
    pdf_url: str


def _clean_optional(value: str) -> str:
    value = value.strip()
    return "" if value in EMPTY_RESPONSES else value


def parse_fields(body: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(body))
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = match.group(1)
        if label in fields:
            raise SubmissionError(f"duplicate reserved heading: {label}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        fields[label] = body[match.end():end].strip()
    return fields


def validate_summary(summary: str) -> str:
    summary = summary.strip()
    if not 20 <= len(summary) <= 4000:
        raise SubmissionError("summary must be between 20 and 4000 characters")
    if CONTROL_RE.search(summary):
        raise SubmissionError("summary contains disallowed control characters")
    if RAW_HTML_RE.search(summary):
        raise SubmissionError("raw HTML is not allowed in summaries")
    if DANGEROUS_SCHEME_RE.search(summary):
        raise SubmissionError("dangerous URL scheme is not allowed in summaries")
    if IMAGE_MARKDOWN_RE.search(summary):
        raise SubmissionError("Markdown images are not allowed in summaries")
    for target in MARKDOWN_LINK_RE.findall(summary):
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SubmissionError("Markdown links must use absolute HTTP(S) URLs")
    return summary


def normalize_doi(value: str) -> str | None:
    value = _clean_optional(value)
    if not value:
        return None
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip()
            break
    if not DOI_RE.fullmatch(value):
        raise SubmissionError("evidence DOI is invalid")
    return value


def parse_issue(issue: dict) -> Submission:
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")

    if title.startswith("[Reproduction]"):
        kind = "reproduction"
    elif title.startswith("[Artifact review]"):
        kind = "artifact_review"
    else:
        raise SubmissionError("unsupported PaperTrust issue type")

    fields = parse_fields(body)
    required = {"arXiv ID", "Paper version", "Tags", "Summary"}
    if kind == "reproduction":
        required.add("Result")
    missing = sorted(required - fields.keys())
    if missing:
        raise SubmissionError("missing section(s): " + ", ".join(missing))

    arxiv_id = fields["arXiv ID"].strip()
    if not ARXIV_ID_RE.fullmatch(arxiv_id):
        raise SubmissionError("invalid arXiv ID")

    requested_version = fields["Paper version"].strip().lower()
    if requested_version != "latest" and not VERSION_RE.fullmatch(requested_version):
        raise SubmissionError("paper version must be 'latest' or look like v1, v2, ...")

    tags = tuple(item.strip() for item in fields["Tags"].split(",") if item.strip())
    if not tags:
        raise SubmissionError("at least one tag is required")
    unknown = sorted(set(tags) - ALLOWED_TAGS)
    if unknown:
        raise SubmissionError("unknown tags: " + ", ".join(unknown))

    result = None
    if kind == "reproduction":
        result = fields["Result"].strip()
        if result not in ALLOWED_RESULTS:
            raise SubmissionError("invalid reproduction result")

    summary = validate_summary(fields["Summary"])
    evidence_doi = normalize_doi(fields.get("Evidence DOI", ""))

    return Submission(
        kind=kind,
        arxiv_id=arxiv_id,
        paper_version=requested_version,
        tags=tags,
        summary=summary,
        evidence_doi=evidence_doi,
        result=result,
    )


class _CitationMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        attributes = {key.lower(): value for key, value in attrs if value is not None}
        name = attributes.get("name", "").lower()
        content = attributes.get("content", "")
        if name.startswith("citation_") and content:
            self.values.setdefault(name, []).append(html.unescape(content))


def fetch_arxiv_metadata(arxiv_id: str, paper_version: str) -> ArxivMetadata:
    if not ARXIV_ID_RE.fullmatch(arxiv_id):
        raise SubmissionError("invalid arXiv ID")
    if not VERSION_RE.fullmatch(paper_version):
        raise SubmissionError("invalid paper version")

    safe_id = urllib.parse.quote(arxiv_id, safe="/")
    request = urllib.request.Request(
        f"https://arxiv.org/abs/{safe_id}{paper_version}",
        headers={"User-Agent": "PaperTrust/1.0 (god@papertrust.org)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            page = response.read(2_000_000).decode("utf-8", errors="replace")
    except Exception as exc:
        raise SubmissionError("could not resolve arXiv metadata") from exc

    parser = _CitationMetaParser()
    parser.feed(page)
    values = parser.values

    def one(name: str) -> str:
        items = values.get(name, [])
        return " ".join(items[0].split()) if items else ""

    title = one("citation_title")
    abstract = one("citation_abstract")
    authors = tuple(
        " ".join(author.split())
        for author in values.get("citation_author", [])
        if author.strip()
    )
    if not title or not abstract or not authors:
        raise SubmissionError("arXiv metadata is incomplete")

    return ArxivMetadata(
        title=title,
        authors=authors,
        abstract=abstract,
        pdf_url=f"https://arxiv.org/pdf/{safe_id}{paper_version}",
    )


def latest_arxiv_version(arxiv_id: str) -> str:
    if not ARXIV_ID_RE.fullmatch(arxiv_id):
        raise SubmissionError("invalid arXiv ID")

    safe_id = urllib.parse.quote(arxiv_id, safe="/")
    request = urllib.request.Request(
        f"https://arxiv.org/abs/{safe_id}",
        headers={"User-Agent": "PaperTrust/1.0 (god@papertrust.org)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            page = response.read(2_000_000).decode("utf-8", errors="replace")
    except Exception as exc:
        raise SubmissionError("could not resolve the latest arXiv version") from exc

    decoded = html.unescape(page)
    escaped = re.escape(arxiv_id)
    versions = {int(value) for value in re.findall(escaped + r"v([1-9][0-9]*)", decoded)}
    versions.update(int(value) for value in re.findall(r"\[v([1-9][0-9]*)\]", decoded))
    if not versions:
        raise SubmissionError("could not determine the latest arXiv version")
    return f"v{max(versions)}"


def resolve_paper_version(arxiv_id: str, requested: str) -> str:
    latest = latest_arxiv_version(arxiv_id)
    latest_num = int(latest[1:])
    if requested == "latest":
        return latest

    match = VERSION_RE.fullmatch(requested)
    if not match:
        raise SubmissionError("invalid paper version")
    if int(match.group(1)) > latest_num:
        raise SubmissionError(f"paper version {requested} does not exist; latest is {latest}")
    return requested


def build_record(submission: Submission) -> dict:
    paper_version = resolve_paper_version(submission.arxiv_id, submission.paper_version)
    record: dict[str, object] = {
        "type": submission.kind,
        "paper_version": paper_version,
        "tags": list(submission.tags),
        "summary": submission.summary,
    }
    if submission.result is not None:
        record["result"] = submission.result
    if submission.evidence_doi is not None:
        record["evidence"] = [submission.evidence_doi]
    return record
