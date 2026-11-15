"""pandera data contracts accept the clean tables and reject contract violations."""

import numpy as np
import pandas as pd
import pandera.errors as pae
import pytest
from conftest import read_raw

from mgcomb.clean.cfig import clean_cfig
from mgcomb.clean.flex import clean_flex
from mgcomb.schemas import CFIG_SCHEMA, FLEX_SCHEMA


@pytest.fixture(scope="module")
def flex() -> pd.DataFrame:
    return clean_flex(read_raw("flex"))


@pytest.fixture(scope="module")
def cfig() -> pd.DataFrame:
    return clean_cfig(read_raw("cfig_normal"), read_raw("cfig_inverse"))


def test_clean_tables_validate(flex, cfig):
    FLEX_SCHEMA.validate(flex, lazy=True)
    CFIG_SCHEMA.validate(cfig, lazy=True)


@pytest.mark.parametrize(
    "column,value",
    [
        ("fuel", "dodecane"),
        ("outcome", "fizzle"),
        ("x_o2", 0.05),
        ("pressure_atm", 4.0),
        ("d0_mm", 7.5),
        ("burning_rate_K_mm2_s", 2.0),
        ("burn_time_s", 61.0),
        ("test_uid", "20CAL10"),  # duplicate uid
    ],
)
def test_flex_schema_rejects(flex, column, value):
    bad = flex.copy()
    bad.loc[0, column] = value
    with pytest.raises(pae.SchemaErrors):
        FLEX_SCHEMA.validate(bad, lazy=True)


def test_flex_schema_rejects_mole_fraction_sum(flex):
    bad = flex.copy()
    bad.loc[0, "x_n2"] = 0.70  # sum 0.91
    with pytest.raises(pae.SchemaErrors):
        FLEX_SCHEMA.validate(bad, lazy=True)


def test_flex_schema_rejects_column_order(flex):
    cols = list(flex.columns)
    cols[0], cols[1] = cols[1], cols[0]
    with pytest.raises((pae.SchemaError, pae.SchemaErrors)):
        FLEX_SCHEMA.validate(flex[cols], lazy=True)


def test_flex_schema_allows_null_pressure(flex):
    ok = flex.copy()
    ok.loc[0, "pressure_atm"] = np.nan
    FLEX_SCHEMA.validate(ok, lazy=True)


@pytest.mark.parametrize(
    "column,value",
    [("flame_type", "sideways"), ("end", "SE"), ("hot_ignition", 2), ("test_id", "21088 B1"), ("zst", 1.5)],
)
def test_cfig_schema_rejects(cfig, column, value):
    bad = cfig.copy()
    bad.loc[0, column] = value
    with pytest.raises(pae.SchemaErrors):
        CFIG_SCHEMA.validate(bad, lazy=True)
