"""Read the NASA PSI tables from data/raw/ exactly as the CSVs say (no cleaning)."""

import pandas as pd

from mgcomb.paths import RAW

RAW_FILES: dict[str, str] = {
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


def load_raw(table_id: str) -> pd.DataFrame:
    """Load one raw table by id (see RAW_FILES).

    Values, headers and dtypes are pandas' default reading of the file. The only change is dropping
    rows that are entirely empty (the CFI-G inverse file has ~860 trailing `,,,` lines); the index is
    then reset.
    """
    try:
        name = RAW_FILES[table_id]
    except KeyError:
        raise KeyError(f"unknown table id {table_id!r}; expected one of {sorted(RAW_FILES)}") from None
    return pd.read_csv(RAW / name).dropna(how="all").reset_index(drop=True)
