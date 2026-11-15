"""Clean the FLEX droplet table (PSI-69). Contract: CLAUDE.md, "FLEX clean"."""

import logging

import pandas as pd

from mgcomb.clean._common import flag_counts, join_flags, to_numeric

log = logging.getLogger(__name__)

CONTRACT_COLUMNS: list[str] = [
    "test_id",
    "date",
    "fuel",
    "pressure_atm",
    "x_o2",
    "x_n2",
    "x_co2",
    "x_he",
    "d0_mm",
    "d_ext_mm",
    "burning_rate_K_mm2_s",
    "burn_time_s",
    "outcome",
    "dext_over_d0",
]
EXTRA_COLUMNS: list[str] = ["test_uid", "d_ext_valid", "qc_flags"]

MMHG_PER_ATM = 760.0
# Flag mole-fraction sums this far from 1 (the ~0.98 rows); the contract tolerance is 0.025.
MOLE_SUM_FLAG = 0.015

_RAW_NUMERIC = {
    "x_o2": "O initial ambient composition; mole fraction",
    "x_n2": "N initial ambient composition; mole fraction",
    "x_co2": "CO initial ambient composition; mole fraction",
    "x_he": "He initial ambient composition; mole fraction",
    "d0_mm": "Droplet initial diameter; mm",
    "d_ext_mm": "Visible flame extinction diameter; mm",
    # Labeled "mm" in the raw file, but it is the d²-law burning-rate constant K
    # in mm²/s (values 0.05 to 1.06).
    "burning_rate_K_mm2_s": "Burning rate; mm",
    "burn_time_s": "Burn time; s",
}


def clean_flex(raw: pd.DataFrame) -> pd.DataFrame:
    """Tidy FLEX table: one row per test, 274 rows, oracle-compatible values.

    Units: pressure in atm (raw mmHg / 760), diameters in mm, K in mm²/s, burn time in s.
    Rows are never dropped; known quirks are listed in `qc_flags` (semicolon-joined, '' when clean).
    """
    raw = raw.reset_index(drop=True)
    test_id = raw["FLEX Identifier"].astype(str).str.strip()
    test_no = raw["FLEX Test #"].astype(int)

    # Mixed date formats: the 2-digit-year rows (e.g. 10/24/09) don't parse and become null, as in the oracle.
    date = pd.to_datetime(raw["Test Date"].astype(str).str.strip(), format="%m/%d/%Y", errors="coerce")

    pressure_mmhg = to_numeric(raw["Ambient pressure; mmHg"])
    # Two burn times are logged as approximate ("~6", "~9"); the oracle turned them into null, so we do too.
    burn_raw = raw[_RAW_NUMERIC["burn_time_s"]].astype("string").str.strip()
    burn_approx = burn_raw.str.startswith("~").fillna(False)
    num = {
        k: to_numeric(raw[c].mask(burn_approx) if k == "burn_time_s" else raw[c])
        for k, c in _RAW_NUMERIC.items()
    }

    out = pd.DataFrame(
        {
            "test_id": test_id,
            "date": date,
            "fuel": raw["Fuel"].astype(str).str.strip().str.lower(),
            # 0 mmHg is a logging error, so it becomes null.
            "pressure_atm": (pressure_mmhg / MMHG_PER_ATM).where(pressure_mmhg > 0),
            **num,
            "outcome": raw["Test end"].astype(str).str.strip().str.lower(),
        }
    )
    out["dext_over_d0"] = out.d_ext_mm / out.d0_mm

    dup = test_id.duplicated(keep=False)
    out["test_uid"] = test_id.where(~dup, test_id + "#" + test_no.astype(str))
    out["d_ext_valid"] = (out.outcome == "extinction").astype(bool)

    mole_sum = out[["x_o2", "x_n2", "x_co2", "x_he"]].sum(axis=1)
    out["qc_flags"] = join_flags(
        {
            "pressure_zero_logged": pressure_mmhg == 0,
            "duplicate_test_id": dup,
            "dext_gt_d0": out.d_ext_mm > out.d0_mm,
            "dext_non_extinction": out.d_ext_mm.notna() & ~out.d_ext_valid,
            "date_unparsed": out.date.isna(),
            "burn_time_approx": burn_approx,
            "mole_fraction_sum_off": (mole_sum - 1).abs() >= MOLE_SUM_FLAG - 1e-9,
        },
        out.index,
    )
    log.info("clean_flex: %d rows kept, flags %s", len(out), flag_counts(out.qc_flags))
    return out[CONTRACT_COLUMNS + EXTRA_COLUMNS]
