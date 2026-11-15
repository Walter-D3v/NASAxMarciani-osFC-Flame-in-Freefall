"""clean_cfig: unified normal + inverse CFI-G table."""

import pandas as pd
import pytest
from conftest import read_raw

from mgcomb.clean.cfig import CONTRACT_COLUMNS, clean_cfig


@pytest.fixture(scope="module")
def cfig() -> pd.DataFrame:
    return clean_cfig(read_raw("cfig_normal"), read_raw("cfig_inverse"))


def _flagged(df: pd.DataFrame, flag: str) -> pd.DataFrame:
    return df[df.qc_flags.str.split(";").apply(lambda fl: flag in fl)]


def test_shape_and_columns(cfig):
    assert len(cfig) == 333
    assert cfig.flame_type.value_counts().to_dict() == {"normal": 179, "inverse": 154}
    assert list(cfig.columns) == [*CONTRACT_COLUMNS, "qc_flags"]
    assert isinstance(cfig.index, pd.RangeIndex)


def test_test_ids_have_no_spaces_and_are_unique(cfig):
    assert not cfig.test_id.str.contains(r"\s").any()
    assert cfig.test_id.is_unique
    assert "21088B1" in set(cfig.test_id)


def test_hot_ignition_mapping(cfig):
    assert set(cfig.hot_ignition) == {0, 1}
    assert cfig.groupby("flame_type").hot_ignition.sum().to_dict() == {"inverse": 131, "normal": 132}
    flash = _flagged(cfig, "hot_ignition_flash")
    assert len(flash) == 8
    assert (flash.hot_ignition == 0).all()


def test_end_and_binary_columns(cfig):
    assert cfig.end.value_counts().to_dict() == {
        "self_extinction": 183,
        "flow_terminated": 89,
        "no_flame": 61,
    }
    assert cfig.cool_flame.sum() == 7
    assert cfig.thin_filament_pyrometry.sum() == 30


def test_div0_tad_zst_null_and_flagged(cfig):
    bad = _flagged(cfig, "tad_zst_div0")
    assert sorted(bad.test_id) == ["21125A4", "21125H3"]
    assert bad[["tad_K", "zst"]].isna().all().all()
    assert cfig.tad_K.isna().sum() == 2


def test_header_variants_are_normalized():
    """Extra or missing spaces in headers must not change the result."""
    n, i = read_raw("cfig_normal"), read_raw("cfig_inverse")
    n2 = n.rename(columns=lambda c: "  " + c.replace(" ", "   ") + " ")
    i2 = i.rename(columns={"Self -ext or flow term": "Self-ext or flow term"})
    pd.testing.assert_frame_equal(clean_cfig(n2, i2), clean_cfig(n, i))


def test_unknown_hot_ignition_value_raises():
    n = read_raw("cfig_normal").copy()
    n.loc[n.index[0], "Hot ignition"] = "maybe"
    with pytest.raises(ValueError, match="Hot ignition"):
        clean_cfig(n, read_raw("cfig_inverse"))
