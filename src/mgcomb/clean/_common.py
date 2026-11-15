"""Helpers shared by the cleaners."""

from collections.abc import Iterable

import numpy as np
import pandas as pd

# Missing-value markers seen in the raw PSI tables: U+FFFD is a mis-encoded dash in FLEX.
MISSING_TOKENS: frozenset[str] = frozenset({"�", "-", ""})


def to_numeric(s: pd.Series, extra_missing: Iterable[str] = ()) -> pd.Series:
    """Parse a raw column to float, mapping known missing markers to NaN.

    Unlike `pd.to_numeric(errors="coerce")`, any other non-numeric token raises, so new junk in the raw files
    fails loudly instead of silently becoming null.
    """
    missing = MISSING_TOKENS | set(extra_missing)
    text = s.astype("string").str.strip()
    text = text.mask(text.isin(missing))
    out = pd.to_numeric(text, errors="coerce")
    bad = text.notna() & out.isna()
    if bad.any():
        raise ValueError(f"{s.name}: unexpected non-numeric values {sorted(set(text[bad]))[:10]}")
    return out.astype("float64").fillna(np.nan)


def join_flags(flags: dict[str, pd.Series], index: pd.Index) -> pd.Series:
    """Combine boolean flag masks into one semicolon-joined string column ('' when no flag)."""
    out = pd.Series([""] * len(index), index=index, dtype="string")
    for name, mask in flags.items():
        m = mask.fillna(False).astype(bool)
        out[m] = out[m].where(out[m] == "", out[m] + ";") + name
    return out.astype(str)


def flag_counts(qc_flags: pd.Series) -> dict[str, int]:
    """Count how many rows carry each flag."""
    parts = qc_flags[qc_flags != ""].str.split(";").explode()
    return {k: int(v) for k, v in parts.value_counts().sort_index().items()}
