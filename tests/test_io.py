"""mgcomb.io.load_raw and mgcomb.paths: raw tables load exactly as the CSV says."""

import pandas as pd
import pytest
from conftest import RAW, RAW_FILES, read_raw

from mgcomb import io, paths


def test_paths_point_at_repo_data():
    assert paths.RAW == RAW
    assert paths.RAW.is_dir()
    assert paths.PROCESSED == paths.DATA / "processed"
    assert (paths.ROOT / "pyproject.toml").is_file()


def test_raw_files_registry_matches_conftest():
    assert io.RAW_FILES == RAW_FILES


@pytest.mark.parametrize("table_id", sorted(RAW_FILES))
def test_load_raw_equals_plain_read(table_id):
    got = io.load_raw(table_id)
    pd.testing.assert_frame_equal(got, read_raw(table_id).reset_index(drop=True))


def test_load_raw_keeps_raw_values():
    """No cleaning: stray spaces, mis-encoded dashes and odd casing survive."""
    flex = io.load_raw("flex")
    assert (flex["Visible flame extinction diameter; mm"] == "�").sum() == 28
    inv = io.load_raw("cfig_inverse")
    assert "Self -ext or flow term" in inv.columns
    assert inv["Test"].str.contains(" ").all()
    assert set(inv["Hot ignition"]) == {"Yes", "yes", "No", "no", "flash"}


def test_load_raw_unknown_id():
    with pytest.raises(KeyError, match="unknown table id"):
        io.load_raw("nope")
