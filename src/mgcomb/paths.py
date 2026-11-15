"""Repo-relative paths (pathlib only, so they work on Windows and Linux)."""

from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
DATA: Path = ROOT / "data"
RAW: Path = DATA / "raw"
PROCESSED: Path = DATA / "processed"
PSI117: Path = DATA / "PSI-117"
REFERENCE_EXPECTED: Path = ROOT / "reference" / "expected"
