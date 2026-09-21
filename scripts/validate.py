#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import re
import sys

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schema" / "paper.json").read_text())
NEW_ID = re.compile(r"^(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+/[0-9]{7})$")


def arxiv_id_from_path(path: pathlib.Path) -> str:
    rel = path.relative_to(ROOT / "papers")
    if len(rel.parts) == 1:
        arxiv_id = rel.stem
    elif len(rel.parts) == 2:
        arxiv_id = f"{rel.parts[0]}/{path.stem}"
    else:
        raise ValueError("paper files must map directly to an arXiv identifier")
    if not NEW_ID.fullmatch(arxiv_id):
        raise ValueError(f"invalid arXiv identifier encoded by path: {arxiv_id}")
    return arxiv_id


def validate(path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    try:
        arxiv_id_from_path(path)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:
        return [f"invalid YAML: {exc}"]

    validator = jsonschema.Draft202012Validator(SCHEMA)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = ".".join(map(str, error.absolute_path)) or "<root>"
        errors.append(f"{where}: {error.message}")
    return errors


def main() -> int:
    files = sorted((ROOT / "papers").rglob("*.yaml"))
    if not files:
        print("No paper records yet.")
        return 0

    failed = False
    for path in files:
        errors = validate(path)
        if errors:
            failed = True
            print(f"FAIL {path.relative_to(ROOT)}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
