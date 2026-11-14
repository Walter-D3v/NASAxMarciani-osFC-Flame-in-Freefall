# mgcomb: microgravity combustion analytics

NASA PSI microgravity combustion data (FLEX droplets, ACME CFI-G gas flames): cleaning, baseline ML models and a
Streamlit dashboard. Built with Claude Code; start with **CLAUDE.md** and **docs/ROADMAP.md**.

```
uv sync
uv run pytest -q          # raw-data guards pass; regression tests skip until src/mgcomb is built
uv run pytest -q -m slow  # oracle: re-runs reference/scripts and diffs against reference/expected
```

Data: NASA Physical Sciences Informatics (https://psi.nasa.gov), CC0-1.0. Cite each investigation's DOI
(see data/raw/meta.json).
