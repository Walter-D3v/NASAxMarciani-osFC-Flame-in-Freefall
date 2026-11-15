"""clean_flex: contract from CLAUDE.md plus every known FLEX quirk."""

import numpy as np
import pandas as pd
import pytest
from conftest import read_raw

from mgcomb.clean.flex import CONTRACT_COLUMNS, clean_flex


@pytest.fixture(scope="module")
def flex() -> pd.DataFrame:
    return clean_flex(read_raw("flex"))


def _row(flex: pd.DataFrame, test_id: str) -> pd.Series:
    rows = flex[flex.test_id == test_id]
    assert len(rows) == 1, test_id
    return rows.iloc[0]


def _flagged(flex: pd.DataFrame, flag: str) -> pd.DataFrame:
    return flex[flex.qc_flags.str.split(";").apply(lambda fl: flag in fl)]


def test_shape_and_column_order(flex):
    assert len(flex) == 274
    assert list(flex.columns[: len(CONTRACT_COLUMNS)]) == CONTRACT_COLUMNS
    assert list(flex.columns[len(CONTRACT_COLUMNS) :]) == ["test_uid", "d_ext_valid", "qc_flags"]
    assert isinstance(flex.index, pd.RangeIndex)


def test_categoricals(flex):
    assert set(flex.fuel) == {"methanol", "heptane"}
    assert set(flex.outcome) == {"extinction", "disruption", "completion"}
    assert flex.outcome.value_counts().to_dict() == {"extinction": 186, "disruption": 61, "completion": 27}


def test_missing_markers_become_null(flex):
    assert flex.d_ext_mm.isna().sum() == 77
    assert flex.d0_mm.isna().sum() == 12
    for c in ["d0_mm", "d_ext_mm", "burn_time_s"]:
        assert pd.api.types.is_float_dtype(flex[c]), c


def test_quirk1_zero_pressure_is_null_and_flagged(flex):
    r = _row(flex, "C11M201")
    assert np.isnan(r.pressure_atm)
    assert flex.pressure_atm.isna().sum() == 1
    assert _flagged(flex, "pressure_zero_logged").test_id.tolist() == ["C11M201"]


def test_quirk2_duplicate_id_gets_distinct_uid(flex):
    dup = flex[flex.test_id == "193F001"]
    assert len(dup) == 2
    assert dup.test_uid.tolist() == ["193F001#70", "193F001#73"]
    assert flex.test_uid.is_unique
    assert (_flagged(flex, "duplicate_test_id").test_id == "193F001").all()
    assert len(_flagged(flex, "duplicate_test_id")) == 2
    single = flex[flex.test_id != "193F001"]
    assert (single.test_uid == single.test_id).all()


def test_quirk3_dext_larger_than_d0_is_kept_and_flagged(flex):
    r = _row(flex, "C13H102")
    assert r.d_ext_mm == pytest.approx(3.34)
    assert r.d0_mm == pytest.approx(3.33)
    assert _flagged(flex, "dext_gt_d0").test_id.tolist() == ["C13H102"]


def test_quirk4_dext_on_non_extinction_rows(flex):
    assert (flex.d_ext_valid == (flex.outcome == "extinction")).all()
    assert flex.d_ext_valid.dtype == bool
    bad = _flagged(flex, "dext_non_extinction")
    assert len(bad) == 38
    assert bad.outcome.value_counts().to_dict() == {"disruption": 24, "completion": 14}
    assert (bad.d_ext_mm == 0).sum() == 8  # raw value kept, 0.0 = "no extinction"


def test_quirk5_unparseable_dates_null_and_flagged(flex):
    assert flex.date.isna().sum() == 50
    assert pd.api.types.is_datetime64_any_dtype(flex.date)
    assert (_flagged(flex, "date_unparsed").index == flex.index[flex.date.isna()]).all()


def test_quirk6_low_mole_fraction_sums_kept(flex):
    s = flex[["x_o2", "x_n2", "x_co2", "x_he"]].sum(axis=1)
    assert ((s - 1).abs() <= 0.025).all()
    low = _flagged(flex, "mole_fraction_sum_off")
    assert sorted(low.test_id) == sorted(["193R002", "203R002", "203F001", "179F001", "207F001", "207F002"])


def test_approximate_burn_times_null_and_flagged(flex):
    """Not in the CLAUDE.md quirk list: raw burn times '~6' and '~9'. The oracle made them null."""
    approx = _flagged(flex, "burn_time_approx")
    assert sorted(approx.test_id) == ["H01H102", "H01M104"]
    assert approx.burn_time_s.isna().all()


def test_unflagged_rows_have_empty_string(flex):
    assert flex.qc_flags.notna().all()
    assert (flex.qc_flags == "").sum() > 100


def test_pure_function_does_not_mutate_input():
    raw = read_raw("flex")
    before = raw.copy()
    clean_flex(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_unexpected_token_raises():
    raw = read_raw("flex").copy()
    raw.loc[raw.index[0], "Burn time; s"] = "n/a"
    with pytest.raises(ValueError, match="Burn time"):
        clean_flex(raw)
