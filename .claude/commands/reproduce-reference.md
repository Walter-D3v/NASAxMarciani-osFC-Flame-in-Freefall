---
description: Re-run the prototype scripts in reference/scripts into a temp directory and diff their outputs against reference/expected
---

Prove the environment still reproduces the prototype:

1. Run `uv run pytest -q -m slow tests/test_oracle.py`.
2. If it fails, show which file and which columns or metrics differ, and by how much. Likely causes to check: a
   different scikit-learn or pandas version (compare with `uv pip list`), float formatting, or a platform
   difference (Windows line endings).
3. Never edit anything in `reference/`. If you believe the oracle is wrong, explain why in your report.
