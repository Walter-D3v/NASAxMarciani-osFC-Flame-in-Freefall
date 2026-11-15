"""pandera schemas: the data contracts in CLAUDE.md, executable."""

import pandera.pandas as pa

from mgcomb.clean.cfig import CONTRACT_COLUMNS as CFIG_COLUMNS
from mgcomb.clean.flex import CONTRACT_COLUMNS as FLEX_COLUMNS
from mgcomb.clean.flex import EXTRA_COLUMNS as FLEX_EXTRA

MOLE_SUM_TOL = 0.025


def _num(lo: float | None = None, hi: float | None = None, nullable: bool = True) -> pa.Column:
    checks = []
    if lo is not None and hi is not None:
        checks.append(pa.Check.in_range(lo, hi))
    elif lo is not None:
        checks.append(pa.Check.ge(lo))
    return pa.Column(float, checks=checks, nullable=nullable)


def _mole_sum_ok(df) -> bool:
    s = df[["x_o2", "x_n2", "x_co2", "x_he"]].sum(axis=1)
    return ((s - 1).abs() <= MOLE_SUM_TOL + 1e-9).all()


FLEX_SCHEMA = pa.DataFrameSchema(
    {
        "test_id": pa.Column(str, pa.Check.str_matches(r"^\S+$")),
        "date": pa.Column("datetime64[us]", nullable=True),
        "fuel": pa.Column(str, pa.Check.isin(["methanol", "heptane"])),
        "pressure_atm": _num(0.6, 3.2),
        "x_o2": _num(0.10, 0.40, nullable=False),
        "x_n2": _num(0.0, 1.0, nullable=False),
        "x_co2": _num(0.0, 1.0, nullable=False),
        "x_he": _num(0.0, 1.0, nullable=False),
        "d0_mm": _num(0.5, 6.0),
        # 0.0 is a raw "no extinction" marker on non-extinction rows (see d_ext_valid).
        "d_ext_mm": _num(0.0, 6.0),
        "burning_rate_K_mm2_s": _num(0.03, 1.2),
        "burn_time_s": _num(0.0, 60.0),
        "outcome": pa.Column(str, pa.Check.isin(["extinction", "disruption", "completion"])),
        "dext_over_d0": _num(0.0),
        "test_uid": pa.Column(str, unique=True),
        "d_ext_valid": pa.Column(bool),
        "qc_flags": pa.Column(str),
    },
    checks=[pa.Check(_mole_sum_ok, name="mole_fractions_sum_to_1")],
    strict=True,
    ordered=True,
    name="flex_clean",
)
assert list(FLEX_SCHEMA.columns) == FLEX_COLUMNS + FLEX_EXTRA

CFIG_SCHEMA = pa.DataFrameSchema(
    {
        "flame_type": pa.Column(str, pa.Check.isin(["normal", "inverse"])),
        "test_id": pa.Column(str, pa.Check.str_matches(r"^\S+$"), unique=True),
        "fuel": pa.Column(str, pa.Check.str_matches(r"^(\d+% )?(ethane|propane|butane)$")),
        "pressure_bar": _num(0.3, 4.0, nullable=False),
        "tad_K": _num(1000.0, 3500.0),
        "zst": _num(0.0, 1.0),
        "hot_ignition": pa.Column(int, pa.Check.isin([0, 1])),
        "cool_flame": pa.Column(int, pa.Check.isin([0, 1])),
        "burn_time_s": _num(0.0),
        "end": pa.Column(str, pa.Check.isin(["self_extinction", "flow_terminated", "no_flame"])),
        "thin_filament_pyrometry": pa.Column(int, pa.Check.isin([0, 1])),
        "comments": pa.Column(str, nullable=True),
        "qc_flags": pa.Column(str),
    },
    strict=True,
    ordered=True,
    name="cfig_clean",
)
assert list(CFIG_SCHEMA.columns) == [*CFIG_COLUMNS, "qc_flags"]
