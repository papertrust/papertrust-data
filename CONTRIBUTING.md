# Contributing records

PaperTrust accepts evidence-backed records about reproducibility and public research artifacts.

## Principles

- One paper file per arXiv identifier.
- Every reproduction or artifact-review record must resolve to an exact arXiv paper version. The submission UI defaults to the latest version.
- Every record needs a concise human-readable Markdown summary. Raw HTML, embedded images, dangerous URL schemes, control characters, and reserved PaperTrust field headings are rejected.
- Machine-readable `result` and `tags` are required where applicable.
- A version-specific evidence DOI is encouraged when independent archived evidence exists, but it is not mandatory.
- Do not label people or papers as fraudulent, dishonest, fake, or untrustworthy.
- State observable and reviewable facts.
- Issues must be created from the submitter's own GitHub account. Pull requests are opened mechanically by GitHub Actions after format validation.

## Workflow

1. Open a structured issue in this repository from your own GitHub account.
2. GitHub Actions validates the submission format.
3. Invalid issues are closed automatically. Valid issues receive `status:format-valid`.
4. The same workflow converts the issue into canonical YAML and creates or updates a mechanical pull request.
5. At least two authorized reviewers must approve the PR. They review the evidence and the canonical diff.
6. Merging the PR adds the record to the public PaperTrust ledger and automatically closes the source issue.

## Allowed reproduction results

- `reproduced`
- `partially_reproduced`
- `not_reproduced`
- `inconclusive`

## Initial tag vocabulary

- `artifact_missing`
- `artifact_broken`
- `artifact_incomplete`
- `checkpoint_missing`
- `training_code_missing`
- `evaluation_code_missing`
- `raw_results_missing`
- `benchmark_mismatch`
- `metric_mismatch`
- `performance_mismatch`
- `training_mismatch`
- `documentation_incomplete`
- `undocumented_configuration`
- `version_mismatch`
- `independent_reproduction`
- `author_reproduction`
- `corrected`
- `resolved`
- `disputed`

The vocabulary may evolve through ordinary reviewed commits.
