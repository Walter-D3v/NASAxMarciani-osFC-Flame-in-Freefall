---
description: Run the full validation gate (lint, tests, data and model audits) and summarize what blocks the current milestone
argument-hint: [milestone, e.g. M1]
---

Run the validation gate for milestone $ARGUMENTS (if none is given, infer the current milestone from the first
unchecked items in docs/ROADMAP.md).

1. Run `uv run ruff check .` and `uv run pytest -q`. Capture the summaries.
2. Delegate in parallel when the milestone touches them:
   - `data-validator`: for M1 and M4, or any change under src/mgcomb/clean or io.
   - `model-auditor`: for M3, or any change to features or models.
   - `physics-reviewer`: for M2, or any new text or chart that states a physical trend.
3. Merge the results into one report:
   - one verdict line: READY TO CLOSE / NOT READY;
   - a table of each acceptance item for the milestone → pass / fail / not run, with evidence;
   - blocking issues (deduplicated across reviewers), each with the file and the command to reproduce it;
   - the next three actions.
Don't fix anything in this command. Only report.
