# Microgravity Combustion Analytics (mgcomb)

Research project by Fernando: analyze NASA microgravity combustion experiments, train baseline ML models on them,
and present the results in a Streamlit + Plotly dashboard. This repo turns a working prototype (the scripts in
`reference/`) into a tested Python package and app.

**Your job in this repo:** build pipeline components and visualizations, and validate them against the reference
outputs. Correctness of the data and honesty of the model evaluation matter more than speed or polish.

## Data provenance

All data comes from NASA Physical Sciences Informatics (PSI), https://psi.nasa.gov, license CC0-1.0.
`data/raw/` holds the **experimental tables** (one row per test) downloaded on 2026-11-14. The raw imagery
and video (about 12 TB in total) were NOT downloaded.

| Investigation | PSI id | DOI | Raw file(s) | Rows | Status |
|---|---|---|---|---|---|
| FLEX: droplet extinction | PSI-69 | 10.60555/mbq8-0451 | `PSI-69_Experimental table_FLEX.csv` | 274 | **In use**: conditions plus outcomes |
| ACME CFI-G: gas cool flames | PSI-159 | 10.60555/cyt1-kh64 | `..._CFI-G_Normal Flames.csv`, `..._CFI-G_Inverse Flames.csv` | 179 + 154 | **In use**: conditions plus outcomes |
| ACME Flame Design | PSI-10 | 10.60555/w4zy-bt45 | Normal + Inverse | 207 + 120 | Conditions only; soot outcomes live in the raw data |
| BASS-II: solid fuels | PSI-25 | 10.60555/4qc4-de67 | `..._BASS-II.csv` | 129 | Conditions plus O₂/CO₂/CO before and after; not yet used |
| SPICE: smoke points | PSI-107 | 10.60555/9kbh-e962 | `..._Spice.csv` | 469 (34 duplicate rows) | Conditions only |
| CFI: droplet cool flames | PSI-39 | 10.60555/m6pj-a914 | `..._CFI.csv` | 87 | Test log only |
| FLEX-2, s-Flame, CLD, BRE | PSI-68/23/21/20 | see `data/raw/meta.json` | | 8 to 32 | Daily summaries, not modelable |

`data/raw/` is **read-only**. Never edit, re-save or reformat those files. All fixes happen in code.

**Also in `data/`:**
- `data/PSI-117/` (read-only): *Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics* (CFD
  investigation, DOI 10.60555/gz0q-b577). PSI *analyzed* data, which is digitized figure curves (simulation plus
  experiment) of droplet cool flames for n-heptane, n-decane and n-dodecane, from 4 papers (PROCI 2019 ×2,
  PROCI 2023, MST 2024). It is not a per-test table and it is not in `meta.json`. Use it only for physical validation and
  context, never as model training rows. Full documentation and quirks: `docs/PSI-117.md`.
- `data/clean/` is **ignored for now**. It holds byte-identical copies of `data/raw/` and of
  `reference/expected/`, plus a zip of the raw files. Don't read from it in code or tests.

## Repository layout

```
data/raw/              NASA tables as downloaded (read-only) + meta.json (DOIs, publication counts)
data/processed/        pipeline outputs (Parquet + DuckDB), git-ignored, always reproducible
reference/scripts/     prototype: clean.py, models.py, export.py (the "oracle"; do not modify)
reference/expected/    oracle outputs: cleaned tables, predictions, model_summary.json
src/mgcomb/            the package you are building
tests/                 pytest suite; regression tests compare src/mgcomb against reference/expected
docs/ROADMAP.md        milestones with acceptance criteria; work through them in order
docs/PSI-117.md        PSI-117 analyzed data: papers, per-file block layout, quirks, intended use
```

Target package layout. Create modules as milestones need them; don't scaffold empty files ahead of time.

```
src/mgcomb/
  paths.py            repo-relative paths (pathlib only, works on Windows and Linux)
  io.py               load_raw(table_id) -> DataFrame, exactly as the CSV says, no cleaning
  clean/flex.py       clean_flex(raw) -> tidy FLEX table (same contract as reference/expected/flex_droplets.csv)
  clean/cfig.py       clean_cfig(normal, inverse) -> unified CFI-G table
  schemas.py          pandera schemas = the data contracts below
  physics.py          d² law helpers, d2law_check(), unit conversions
  features.py         model feature matrices + group keys for CV
  models.py           train/evaluate baselines; returns metrics dicts shaped like model_summary.json
  store.py            write/read data/processed (Parquet + DuckDB)
  pipeline.py         `python -m mgcomb.pipeline` runs raw -> processed -> models end to end
app/
  Home.py             Streamlit entry; pages/ for FLEX, CFI-G, Models, Anomalies
```

## Stack and commands

Python 3.12, managed with **uv**. Fernando works on Windows, so use `uv run ...` and avoid bash-only syntax in
docs and scripts.

```
uv sync                                  # install
uv run pytest -q                         # all tests (slow oracle test excluded by default)
uv run pytest -q -m slow                 # re-run reference scripts and diff against reference/expected
uv run ruff check . && uv run ruff format --check .
uv run python -m mgcomb.pipeline         # full pipeline (once it exists)
uv run streamlit run app/Home.py         # dashboard (once it exists)
```

Libraries: pandas, numpy, pandera, scikit-learn, duckdb, pyarrow, streamlit, plotly, pytest, ruff. Ask before
adding any other dependency.

## Domain essentials (read before touching data)

- **d² law:** a burning droplet's squared diameter shrinks linearly in time: d² = d₀² − K·t. K is the
  **burning-rate constant** in mm²/s. In the FLEX raw table the column is labeled `Burning rate; mm`; treat it as
  K in mm²/s (values 0.05 to 1.06 fit that).
- **Extinction diameter (d_ext):** the droplet's size when the flame went out. Less O₂ means the flame dies at a
  larger diameter (radiative extinction). It is missing when the test ended in *completion* or *disruption*.
- **FLEX outcomes (`Test end`):** extinction (flame out, droplet left), disruption (droplet broke apart or left
  view), completion (droplet fully burned).
- **Diluents:** He and CO₂ were added to O₂/N₂ atmospheres as suppressants. Derived `diluent` = He if x_he > 0,
  else CO2 if x_co2 > 0, else N2.
- **CFI-G:** *normal* flames issue fuel into oxidizer; *inverse* flames issue oxidizer into fuel. *Hot ignition*
  = the cool flame transitioned to a hot flame. `flash` counts as **no** hot ignition. Tad = adiabatic flame
  temperature (K); Zst = stoichiometric mixture fraction.
- Units: pressure is mmHg in raw FLEX (÷ 760 → atm) and bar in CFI-G. Never mix atm and bar in one column.

## Data contracts (enforce in `schemas.py`, test in `tests/`)

**FLEX clean** (`clean_flex`), 274 rows, columns in this order:
`test_id, date, fuel, pressure_atm, x_o2, x_n2, x_co2, x_he, d0_mm, d_ext_mm, burning_rate_K_mm2_s,
burn_time_s, outcome, dext_over_d0`

- fuel ∈ {methanol, heptane}; outcome ∈ {extinction, disruption, completion}
- pressure_atm in [0.6, 3.2] or null; x_o2 in [0.10, 0.40]; mole fractions sum to 1 ± 0.025
- d0_mm in [0.5, 6]; burning_rate_K_mm2_s in [0.03, 1.2]; burn_time_s in [0, 60]
- Missing values arrive as `�` (a mis-encoded dash) or `-` in the raw file and become null

**Known quirks: keep these rows and flag them, never silently drop them.**
1. One test logs a pressure of **0 mmHg**: a logging error, so it becomes null pressure.
2. `193F001` appears **twice**. The two rows are distinct tests sharing an id, so add a stable suffix in a
   `test_uid` column and keep `test_id` as-is.
3. `C13H102` has **d_ext > d0**: physically impossible, so flag it (`qc_flags`). The oracle kept it (it shows up in
   the d²-law check with ratio −2.721). Reproduce the oracle first, then offer `exclude_flagged=True`.
4. `d_ext_mm` is filled for 38 tests that did **not** end in extinction (24 disruption, 14 completion), and 8 of
   them hold **0.0**, meaning "no extinction". Keep the raw value, but add `d_ext_valid = outcome == 'extinction'`.
5. 50 rows have unparseable dates (mixed formats). The test-id prefix stands in as the day group for CV.
6. 6 rows have mole fractions summing to about 0.98: within tolerance, keep them.

**CFI-G clean** (`clean_cfig`): 333 rows (normal + inverse). `flame_type, test_id, fuel, pressure_bar, tad_K, zst,
hot_ignition (0/1), cool_flame (0/1), burn_time_s, end ∈ {self_extinction, flow_terminated, no_flame},
thin_filament_pyrometry, comments`. Header names differ between the two raw files (spacing, `Self -ext` vs
`Self-ext`), so normalize whitespace before mapping. Test ids contain stray spaces (`21088 B1`), so strip them.

## Modeling rules (non-negotiable)

1. **Grouped cross-validation only.** Split by test day (FLEX: date, falling back to the test-id prefix; CFI-G:
   first 5 characters of the test id). Random K-fold leaks same-session tests and inflates scores.
2. **Always report a naive baseline** next to every score: mean predictor (R², MAE), majority class (accuracy),
   0.5 (AUC).
3. Fixed `random_state=0` everywhere; results must be reproducible to 3 decimals.
4. Report permutation importances as influence, not causation.
5. Never tune hyperparameters on the same folds you report. If you tune, use nested CV.
6. A model that doesn't beat its baseline is a **finding**, not a bug. Report it plainly; don't hide it.

**Reference scores** (`reference/expected/model_summary.json`), the bar for the first rebuild. Match them within
±0.02 before you change anything:

| Model | n | Metric | Score | Baseline |
|---|---|---|---|---|
| FLEX extinction diameter | 196 | R² / MAE mm | 0.709 / 0.418 | 0 / 0.856 |
| FLEX burning-rate K | 257 | R² / MAE mm²/s | 0.595 / 0.060 | 0 / 0.107 |
| FLEX outcome (3 classes) | 261 | accuracy | 0.697 | 0.686 (majority) |
| CFI-G hot ignition | 331 | ROC AUC / accuracy | 0.818 / 0.813 | 0.5 / 0.795 |
| d²-law check | 158 | median K·t / (d₀² − d_ext²) | 1.052 | 1.0 |

**Known oracle flaw (fix in M3, after reproducing it):** the extinction-diameter model trained on all 196 rows
with a d_ext value, including the 38 non-extinction tests. Restricted to extinction tests (n=158) the same model
gives **R² 0.776, MAE 0.337 mm**. M3 reproduces 0.709 first (to prove parity), then switches to the corrected
target and reports both. The reference dashboard still shows 0.709.

## Visualization conventions

- The reference dashboard (built in Claude's Data artifact) is the spec: see `docs/ROADMAP.md`, milestone M4.
- Plotly only; one figure function per chart in `app/charts.py`, each taking a DataFrame and returning a `go.Figure`.
  That keeps charts unit-testable without Streamlit.
- The app **only reads** `data/processed/`. It never cleans, trains or calls the network.
- Every chart has a title that states what it shows, axis titles with units, and hover text with the test id.
- Show counts (n) wherever a share is plotted. Use a colorblind-safe qualitative palette.

## Working agreements

- Work milestone by milestone from `docs/ROADMAP.md`. Write or extend the test first, then the code.
- `reference/` is an oracle: read it, run it, never edit it. If you believe the oracle is wrong, say so and explain
  why; don't "fix" it.
- Before saying a task is done, run `uv run pytest -q` and `uv run ruff check .`, and report the actual output.
- Use subagents (in `.claude/agents/`) for their specialties: `data-validator` after any change to cleaning,
  `model-auditor` after any change to models or features, `physics-reviewer` for anything that claims a physical
  trend, `viz-builder` for app pages, and `pipeline-builder` for implementing src modules.
- Keep functions pure (DataFrame in, DataFrame out). I/O only in `io.py` and `store.py`.
- Commit messages: imperative, one topic per commit. Don't push; Fernando reviews first.
