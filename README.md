# PaperTrust Data

<img src="https://raw.githubusercontent.com/papertrust/papertrust/main/public/brand/logo-mark.svg" width="72" alt="PaperTrust logo">


Public, Git-native records for PaperTrust.

PaperTrust stores only reviewed community records. Paper metadata is resolved from arXiv at display time and is intentionally not duplicated here.

## Data model

Each discussed paper has one YAML file named by its arXiv identifier:

```
papers/2511.15927.yaml
```

Each paper-level record identifies the exact arXiv **paper version it evaluates**. Submission forms default to the latest version, which is resolved to a concrete arXiv version before the canonical record is written.

```yaml
records:
  - type: reproduction
    paper_version: v4
    result: not_reproduced
    tags:
      - performance_mismatch
      - independent_reproduction
    summary: >
      An independent reproduction did not match the reported throughput
      under the documented experimental setup.
    evidence:
      - "10.5281/zenodo.1234567"  # optional but encouraged
```

Git and GitHub already preserve authorship, review, timestamps, issue/PR history, and schema evolution, so those fields are not duplicated in paper files.

## Canonical record

Issues and pull requests are transaction channels. Submitters open issues under their own GitHub identity; format-valid issues automatically produce canonical-record PRs through GitHub Actions. PRs require reviewer approval before merge, and merging closes the source issue. Only merged data on `main` is canonical PaperTrust data.

## Markdown and evidence

`summary` supports Markdown, but PaperTrust deliberately accepts a restricted subset: raw HTML, embedded Markdown images, dangerous URL schemes, control characters, and reserved PaperTrust field headings are rejected. Summaries are always treated as untrusted data.

An evidence DOI is optional so factual public-artifact observations can be recorded before an independent archive exists. A persistent, version-specific evidence DOI is still strongly encouraged whenever one is available.

See [CONTRIBUTING.md](CONTRIBUTING.md) for submission rules.
