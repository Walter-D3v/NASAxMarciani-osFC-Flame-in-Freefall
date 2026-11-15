"""Regression against reference/expected. Each test skips until its module exists (milestones M1 to M3)."""

import json

import numpy as np
import pandas as pd
import pytest
from conftest import EXPECTED, read_raw


def _assert_shared_columns_equal(got: pd.DataFrame, exp: pd.DataFrame, key: str):
    shared = [c for c in exp.columns if c in got.columns]
    assert shared, "no shared columns with the oracle"
    g = got[shared].reset_index(drop=True)
    e = exp[shared].reset_index(drop=True)
    assert len(g) == len(e)
    for c in shared:
        if pd.api.types.is_numeric_dtype(e[c]):
            np.testing.assert_allclose(pd.to_numeric(g[c]), e[c], atol=1e-6, equal_nan=True, err_msg=c)
        else:
            gs = g[c].astype("string").fillna("<NA>")
            es = e[c].astype("string").fillna("<NA>")
            bad = gs != es
            assert not bad.any(), f"{c}: {g.loc[bad, key].tolist()[:10]}"


def test_clean_flex_matches_oracle(expected_flex):
    flex_mod = pytest.importorskip("mgcomb.clean.flex")
    got = flex_mod.clean_flex(read_raw("flex"))
    got = got.assign(date=pd.to_datetime(got["date"]).dt.strftime("%Y-%m-%d"))
    _assert_shared_columns_equal(got, expected_flex, "test_id")


def test_clean_cfig_matches_oracle(expected_cfig):
    cfig_mod = pytest.importorskip("mgcomb.clean.cfig")
    got = cfig_mod.clean_cfig(read_raw("cfig_normal"), read_raw("cfig_inverse"))
    _assert_shared_columns_equal(got, expected_cfig, "test_id")


def test_d2law_matches_oracle(expected_flex):
    physics = pytest.importorskip("mgcomb.physics")
    got = physics.d2law_check(expected_flex)
    exp = pd.read_csv(EXPECTED / "d2law_check.csv")
    assert len(got) == len(exp) == 158
    assert int(got["anomaly"].sum()) == int(exp["anomaly"].sum()) == 22
    assert abs(got["ratio"].median() - exp["ratio"].median()) < 1e-3


@pytest.mark.parametrize(
    "model,metric",
    [
        ("dext", "r2"),
        ("dext", "mae"),
        ("K", "r2"),
        ("K", "mae"),
        ("outcome", "accuracy"),
        ("hot", "auc"),
        ("hot", "accuracy"),
    ],
)
def test_model_scores_match_oracle(model, metric):
    models = pytest.importorskip("mgcomb.models")
    if not hasattr(models, "run_all"):
        pytest.skip("models.run_all not implemented yet")
    ref = json.loads((EXPECTED / "model_summary.json").read_text())
    got = models.run_all(oracle_parity=True)
    assert abs(got[model][metric] - ref[model][metric]) <= 0.02
