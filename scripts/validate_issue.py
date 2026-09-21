#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

from submission import SubmissionError, parse_issue

with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
    event = json.load(handle)

try:
    submission = parse_issue(event["issue"])
except (KeyError, SubmissionError) as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1)

print(submission.kind)
