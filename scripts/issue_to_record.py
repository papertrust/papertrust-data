#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENT = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
ISSUE = EVENT["issue"]
BODY = ISSUE.get("body") or ""
TITLE = ISSUE.get("title") or ""

ARXIV_ID_RE = re.compile(r"(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+/[0-9]{7})")
PAPER_VERSION_RE = re.compile(r"v[1-9][0-9]*")
DOI_RE = re.compile(r"10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+")

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


def field(heading: str) -> str:
    marker = heading + "\n\n"
    if marker not in BODY:
        return ""
    tail = BODY.split(marker, 1)[1]
    return tail.split("\n\n### ", 1)[0].strip()


def paper_path(arxiv_id: str) -> pathlib.Path:
    if "/" in arxiv_id:
        category, number = arxiv_id.split("/", 1)
        return ROOT / "papers" / category / f"{number}.yaml"
    return ROOT / "papers" / f"{arxiv_id}.yaml"


def load_or_create(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"records": []}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ValueError(f"invalid existing paper record: {path}")
    return data


def build_record() -> tuple[str, dict]:
    arxiv_id = field("### arXiv ID")
    tags = [item.strip() for item in field("### Tags").split(",") if item.strip()]
    summary = field("### Summary")
    evidence = field("### Evidence DOI")

    if not ARXIV_ID_RE.fullmatch(arxiv_id):
        raise ValueError("invalid arXiv ID")
    if not tags or any(tag not in ALLOWED_TAGS for tag in tags):
        raise ValueError("invalid or empty tags")
    if len(summary) < 20:
        raise ValueError("summary too short")
    if not DOI_RE.fullmatch(evidence):
        raise ValueError("invalid evidence DOI")

    if "[Reproduction]" in TITLE:
        paper_version = field("### Paper version")
        result = field("### Result")
        if not PAPER_VERSION_RE.fullmatch(paper_version):
            raise ValueError("invalid paper version")
        if result not in ALLOWED_RESULTS:
            raise ValueError("invalid reproduction result")

        return arxiv_id, {
            "type": "reproduction",
            "paper_version": paper_version,
            "result": result,
            "tags": tags,
            "summary": summary,
            "evidence": [evidence],
        }

    if "[Artifact review]" in TITLE:
        return arxiv_id, {
            "type": "artifact_review",
            "tags": tags,
            "summary": summary,
            "evidence": [evidence],
        }

    raise ValueError("unsupported PaperTrust issue type")


def main() -> int:
    arxiv_id, record = build_record()
    path = paper_path(arxiv_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_or_create(path)

    if record in data["records"]:
        print("Equivalent record already exists; nothing to add.")
        return 0

    data["records"].append(record)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000),
        encoding="utf-8",
    )
    print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
