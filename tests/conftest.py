from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
EXPECTED = ROOT / "reference" / "expected"

RAW_FILES = {
    "flex": "PSI-69_Experimental table_FLEX.csv",
    "flex2": "PSI-68_Experimental table_Flex2.csv",
    "cfi": "PSI-39_Experimental table_CFI.csv",
    "sflame": "PSI-23_Experimental table_ACME s-Flame.csv",
    "flame_design_normal": "PSI-10_Experimental table_Flame Design_Normal Flame.csv",
    "flame_design_inverse": "PSI-10_Experimental table_Flame Design_Inverse Flame.csv",
    "cld": "PSI-21_Experimental table_CLD Flame.csv",
    "bre": "PSI-20_Experimental table_ACME BRE.csv",
    "bass2": "PSI-25_Experimental table_BASS-II.csv",
    "spice": "PSI-107_Experimental table_Spice.csv",
    "cfig_normal": "PSI-159_Experimental table_CFI-G_Normal Flames.csv",
    "cfig_inverse": "PSI-159_Experimental table_CFI-G_Inverse Flames.csv",
}


def read_raw(key: str) -> pd.DataFrame:
    return pd.read_csv(RAW / RAW_FILES[key]).dropna(how="all")


@pytest.fixture(scope="session")
def expected_flex() -> pd.DataFrame:
    return pd.read_csv(EXPECTED / "flex_droplets.csv")


@pytest.fixture(scope="session")
def expected_cfig() -> pd.DataFrame:
    return pd.read_csv(EXPECTED / "cfig_gas_flames.csv")
