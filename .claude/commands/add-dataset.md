---
description: Plan onboarding of another PSI experimental table (e.g. BASS-II PSI-25) into the pipeline
argument-hint: <PSI id or raw file name>
---

Onboard the PSI table $ARGUMENTS. Plan first, then wait for approval before writing code.

1. Profile the raw file in `data/raw/`: rows, columns, dtypes, null patterns, encoding artifacts, duplicated rows,
   units in headers, and anything that looks like an outcome versus a condition.
2. Draft a **data contract** in the same style as CLAUDE.md (columns, allowed values, ranges, known quirks).
3. Ask `physics-reviewer` what physical questions this table can answer and which columns are targets versus
   inputs (and which would leak).
4. Propose: the `clean_<name>()` signature, the tests to write, and one baseline model with its grouped-CV key.
5. Present the plan and stop. After approval, implement with `pipeline-builder`, then run `/validate`.
