#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import sys

import yaml

from submission import SubmissionError, build_record, parse_issue

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
        raise SubmissionError(f"invalid existing paper record: {path}")
    return data


def main() -> int:
    event_path = os.environ.get("PAPERTRUST_EVENT_PATH") or os.environ["GITHUB_EVENT_PATH"]
    with open(event_path, encoding="utf-8") as handle:
        event = json.load(handle)

    submission = parse_issue(event["issue"])
    record = build_record(submission)
    path = paper_path(submission.arxiv_id)
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
    except (KeyError, SubmissionError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
