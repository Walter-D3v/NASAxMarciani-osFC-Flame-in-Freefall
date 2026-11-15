"""Clean the ACME CFI-G gaseous flame tables (PSI-159). Contract: CLAUDE.md, "CFI-G clean"."""

import logging
import re

import pandas as pd

from mgcomb.clean._common import flag_counts, join_flags, to_numeric

log = logging.getLogger(__name__)

CONTRACT_COLUMNS: list[str] = [
    "flame_type",
    "test_id",
    "fuel",
    "pressure_bar",
    "tad_K",
    "zst",
    "hot_ignition",
    "cool_flame",
    "burn_time_s",
    "end",
    "thin_filament_pyrometry",
    "comments",
]

# Raw headers keyed by a compact form (lower case, all whitespace removed), so "Self-ext or flow term" and
# "Self -ext or flow term" (normal vs inverse file) map to the same column.
_HEADERS = {
    "test": "Test",
    "fuel": "Fuel",
    "approxp(bar)": "pressure",
    "tad(k)": "tad",
    "zst": "zst",
    "hotignition": "hot",
    "coolflame?": "cool",
    "burntime(sec)": "burn_time",
    "self-extorflowterm": "end",
    "tfp": "tfp",
    "comments": "comments",
}
_HOT = {"yes": 1, "no": 0, "flash": 0}  # a flash is NOT a hot ignition
_END = {"SE": "self_extinction", "FT": "flow_terminated", "-": "no_flame"}
_YES_NO = {"yes": 1, "no": 0}
_DIV0 = "#DIV/0!"


def _compact(header: str) -> str:
    return re.sub(r"\s+", "", header).lower()


def _map_strict(s: pd.Series, mapping: dict, label: str) -> pd.Series:
    out = s.map(mapping)
    bad = out.isna()
    if bad.any():
        raise ValueError(f"{label}: unexpected values {sorted(set(s[bad].astype(str)))[:10]}")
    return out


def _clean_one(g: pd.DataFrame, flame_type: str) -> pd.DataFrame:
    g = g.reset_index(drop=True)
    cols = {_HEADERS[_compact(c)]: c for c in g.columns if _compact(c) in _HEADERS}
    missing = {"Test", "Fuel", "pressure", "tad", "zst", "hot", "burn_time", "end", "tfp"} - set(cols)
    if missing:
        raise KeyError(f"{flame_type}: raw headers not found for {sorted(missing)}")

    hot_raw = g[cols["hot"]].astype(str).str.strip().str.lower()
    cool = (
        g[cols["cool"]]
        .astype("string")
        .str.strip()
        .str.lower()
        .str.startswith("yes")
        .fillna(False)
        .astype(int)
        if "cool" in cols
        else pd.Series(0, index=g.index)  # the inverse file has no cool-flame column
    )
    div0 = (g[cols["tad"]].astype(str).str.strip() == _DIV0) | (
        g[cols["zst"]].astype(str).str.strip() == _DIV0
    )
    comments = g[cols["comments"]] if "comments" in cols else pd.Series(pd.NA, index=g.index, dtype="string")

    out = pd.DataFrame(
        {
            "flame_type": flame_type,
            "test_id": g[cols["Test"]].astype(str).str.replace(r"\s+", "", regex=True),
            "fuel": g[cols["Fuel"]].astype(str).str.strip().str.lower(),
            "pressure_bar": to_numeric(g[cols["pressure"]]),
            "tad_K": to_numeric(g[cols["tad"]], extra_missing=[_DIV0]),
            "zst": to_numeric(g[cols["zst"]], extra_missing=[_DIV0]),
            "hot_ignition": _map_strict(hot_raw, _HOT, "Hot ignition").astype(int),
            "cool_flame": cool,
            "burn_time_s": to_numeric(g[cols["burn_time"]]),
            "end": _map_strict(g[cols["end"]].astype(str).str.strip(), _END, "Self-ext or flow term"),
            "thin_filament_pyrometry": _map_strict(
                g[cols["tfp"]].astype(str).str.strip().str.lower(), _YES_NO, "TFP"
            ).astype(int),
            "comments": comments,
        }
    )
    out["qc_flags"] = join_flags({"tad_zst_div0": div0, "hot_ignition_flash": hot_raw == "flash"}, out.index)
    return out


def clean_cfig(normal: pd.DataFrame, inverse: pd.DataFrame) -> pd.DataFrame:
    """Unified CFI-G table: normal rows first, then inverse (333 rows).

    Units: pressure in bar, Tad in K, burn time in s; zst is dimensionless. Excel `#DIV/0!` in Tad/Zst becomes
    null and is flagged. No rows are dropped.
    """
    out = pd.concat([_clean_one(normal, "normal"), _clean_one(inverse, "inverse")], ignore_index=True)
    log.info("clean_cfig: %d rows kept, flags %s", len(out), flag_counts(out.qc_flags))
    return out[[*CONTRACT_COLUMNS, "qc_flags"]]
