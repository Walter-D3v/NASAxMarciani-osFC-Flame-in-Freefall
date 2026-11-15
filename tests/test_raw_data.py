"""Guards for the read-only NASA tables. These must pass from day one."""

import pytest
from conftest import RAW_FILES, read_raw

EXPECTED_ROWS = {
    "flex": 274,
    "flex2": 8,
    "cfi": 87,
    "sflame": 18,
    "flame_design_normal": 207,
    "flame_design_inverse": 120,
    "cld": 32,
    "bre": 18,
    "bass2": 129,
    "spice": 469,
    "cfig_normal": 179,
    "cfig_inverse": 154,
}


@pytest.mark.parametrize("key", sorted(RAW_FILES))
def test_raw_row_counts(key):
    assert len(read_raw(key)) == EXPECTED_ROWS[key]


def test_flex_raw_columns_present():
    cols = set(read_raw("flex").columns)
    for c in [
        "FLEX Identifier",
        "Fuel",
        "Ambient pressure; mmHg",
        "Droplet initial diameter; mm",
        "Visible flame extinction diameter; mm",
        "Burning rate; mm",
        "Burn time; s",
        "Test end",
    ]:
        assert c in cols, c


def test_flex_known_quirks_still_present():
    """If these fail, the raw file changed: re-check every quirk in CLAUDE.md."""
    f = read_raw("flex")
    assert (f["Ambient pressure; mmHg"] == 0).sum() == 1
    assert f["FLEX Identifier"].str.strip().duplicated().sum() == 1
    assert set(f["Test end"].str.strip()) == {"Extinction", "Disruption", "Completion"}


def test_cfig_headers_differ_between_files():
    """Documents why clean_cfig must normalize headers."""
    n = {c.strip() for c in read_raw("cfig_normal").columns}
    i = {c.strip() for c in read_raw("cfig_inverse").columns}
    assert "Self-ext or flow term" in n
    assert "Self -ext or flow term" in i
