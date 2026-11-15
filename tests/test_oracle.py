"""Slow: re-run the prototype scripts and diff against reference/expected (proves the environment)."""

import json
import shutil
import subprocess
import sys

import pandas as pd
import pytest
from conftest import EXPECTED, RAW, ROOT

pytestmark = pytest.mark.slow


def test_reference_scripts_reproduce(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(RAW, raw)
    (tmp_path / "clean").mkdir()
    (tmp_path / "out").mkdir()
    scripts = ROOT / "reference" / "scripts"
    subprocess.run([sys.executable, str(scripts / "clean.py"), str(raw), str(tmp_path / "clean")], check=True)
    subprocess.run(
        [sys.executable, str(scripts / "models.py"), str(tmp_path / "clean"), str(tmp_path / "out")],
        check=True,
    )
    for name in ["flex_droplets.csv", "cfig_gas_flames.csv"]:
        pd.testing.assert_frame_equal(pd.read_csv(tmp_path / "clean" / name), pd.read_csv(EXPECTED / name))
    got = json.loads((tmp_path / "out" / "model_summary.json").read_text())
    ref = json.loads((EXPECTED / "model_summary.json").read_text())
    for model, keys in {
        "dext": ["r2", "mae"],
        "K": ["r2", "mae"],
        "outcome": ["accuracy"],
        "hot": ["auc"],
        "d2law": ["median_ratio"],
    }.items():
        for k in keys:
            assert abs(got[model][k] - ref[model][k]) < 1e-3, (model, k)
