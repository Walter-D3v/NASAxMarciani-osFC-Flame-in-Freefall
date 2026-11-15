# Roadmap

Work top to bottom. A milestone is done only when every acceptance check passes and the named subagent's review
has no open blocking findings.

## M0: Environment and oracle (½ day) (Fernando)
- [x] `uv sync` works; `uv run pytest -q` passes (the raw-data tests pass, the regression tests skip).
- [x] `uv run pytest -q -m slow` re-runs `reference/scripts/clean.py` and `models.py` into a temp dir and matches
      `reference/expected/` (this proves the environment reproduces the prototype).
- Review: none.

## M1: Load and clean (FLEX, CFI-G) (Fernando)
- [ ] `mgcomb.io.load_raw(table_id)`, with table ids such as `flex`, `cfig_normal`, `cfig_inverse`.
- [ ] `mgcomb.clean.flex.clean_flex` and `mgcomb.clean.cfig.clean_cfig` match the contracts in CLAUDE.md.
- [ ] Add `test_uid` and `qc_flags` (a list or semicolon-joined string) for the known quirks.
- [ ] `mgcomb.schemas` (pandera) validates both outputs. Tests cover every known quirk.
- [ ] Regression: all shared columns equal `reference/expected/flex_droplets.csv` and `cfig_gas_flames.csv`
      (floats within 1e-6).
- Review: **data-validator**.

## M2: Physics and features (Walter)
- [ ] `physics.d2law_check(flex)` reproduces `reference/expected/d2law_check.csv` (158 extinction rows, median
      ratio 1.052, 22 IQR outliers, C13H102 included) by default.
- [ ] `d2law_check(flex, exclude_flagged=True)` drops QC-flagged rows; document how the stats change.
- [ ] `features.flex_matrix()` and `features.cfig_matrix()` return (X, y, groups).
- [ ] Unit tests for the d² law helpers with hand-computed values.
- Review: **physics-reviewer**.

## M3: Baseline models (Fernando)
- [ ] `models.run_all()` returns a dict with the same shape as `model_summary.json`.
- [ ] Scores within ±0.02 of the reference table in CLAUDE.md.
- [ ] Out-of-fold predictions are saved to `data/processed/`.
- [ ] Fix the oracle flaw: extinction-diameter model on `outcome == 'extinction'` only. Expect R² ≈ 0.776, MAE ≈ 0.337
      (n=158). Keep a `--oracle-parity` flag that reproduces 0.709.
- [ ] `pipeline.py` runs raw → processed → models and writes `data/processed/mgcomb.duckdb`.
- Review: **model-auditor**.

## M4: Streamlit dashboard (rebuild of the reference dashboard) (Walter)
Pages and charts:
1. **Home:** KPI cards (FLEX tests 274, 67.9% extinction; CFI-G flames 331, 79.5% hot-ignited; d_ext R²; hot-ignition AUC)
   and a one-sentence takeaway computed from the metrics (e.g. "barely beats" when the gain over baseline is under 0.05).
2. **FLEX:** a fuel filter, then:
   - d_ext vs x_o2, colored by fuel
   - outcome shares by O₂ band (0.12–0.15, 0.16–0.18, 0.19–0.21, 0.23–0.25, 0.30–0.34), with n per bar
   - K vs pressure, colored by diluent
3. **CFI-G:** hot-ignition rate by fuel and flame type; burn time vs Tad, colored by hot ignition.
4. **Models:** score-vs-baseline table; predicted vs measured d_ext with a y = x line; permutation importance with a
   model selector; outcome confusion matrix.
5. **Anomalies:** K·t vs d₀² − d_ext² with outliers highlighted, plus the outlier table sorted by |log ratio|
   (non-positive ratios first).

Acceptance:
- [ ] Each chart function in `app/charts.py` is unit-tested (trace count, axis titles, n labels).
- [ ] The app starts headless (`streamlit run app/Home.py --server.headless true`) without errors.
- Review: **viz-builder** (self-check) then **data-validator** (numbers shown = numbers in processed data).

## M5: Extend (pick after M4)
- [ ] Add BASS-II (PSI-25): clean the table and model flame spread or extinction from O₂/flow conditions.
- [ ] Physics-informed features: dimensionless groups, and a d²-law residual as a feature.
- [ ] Better outcome model: class-balanced metrics (macro F1), calibration, a small hyperparameter search with nested CV.
- [ ] Video pipeline proof of concept: download ONE FLEX test video, extract d(t) with OpenCV, compare to the table.
