#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys

EVENT = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
issue = EVENT["issue"]
body = issue.get("body") or ""
title = issue.get("title") or ""

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
SUPPORTED_TYPES = ("[Reproduction]", "[Artifact review]")

REQUIRED_HEADINGS = [
    "### arXiv ID",
    "### Tags",
    "### Summary",
    "### Evidence DOI",
]

errors = [f"missing section: {heading}" for heading in REQUIRED_HEADINGS if heading not in body]


def field(heading: str) -> str:
    marker = heading + "\n\n"
    if marker not in body:
        return ""
    tail = body.split(marker, 1)[1]
    return tail.split("\n\n### ", 1)[0].strip()


if not any(marker in title for marker in SUPPORTED_TYPES):
    errors.append("unsupported PaperTrust issue type")

arxiv = field("### arXiv ID")
doi = field("### Evidence DOI")
summary = field("### Summary")
tags = [item.strip() for item in field("### Tags").split(",") if item.strip()]

if arxiv and not re.fullmatch(r"(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+/[0-9]{7})", arxiv):
    errors.append("invalid arXiv ID")
if doi and not re.fullmatch(r"10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+", doi):
    errors.append("evidence must be a DOI")
if summary and len(summary) < 20:
    errors.append("summary is too short")
if not tags:
    errors.append("at least one tag is required")
else:
    invalid_tags = sorted(set(tags) - ALLOWED_TAGS)
    if invalid_tags:
        errors.append("unknown tags: " + ", ".join(invalid_tags))

if "[Reproduction]" in title:
    if "### Result" not in body:
        errors.append("missing section: ### Result")
    if "### Paper version" not in body:
        errors.append("missing section: ### Paper version")

    paper_version = field("### Paper version")
    result = field("### Result")
    if paper_version and not re.fullmatch(r"v[1-9][0-9]*", paper_version):
        errors.append("paper version must look like v1, v2, ...")
    if result and result not in ALLOWED_RESULTS:
        errors.append("invalid reproduction result")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print("Issue format is valid.")
