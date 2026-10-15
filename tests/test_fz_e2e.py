"""End-to-end run through fz (fzr) with a fake MORET launcher replaying real MORET 6 outputs.

Checks the whole chain: calculator alias discovery (localhost_Moret), the
arguments fz passes to Moret.sh, the case directories named "radius=...,u5=..."
(a "," breaks the singularity bind of the MORET 6 container scripts: the fake
launcher fails like them), output parsing.

Run: pytest tests/test_fz_e2e.py
"""

import shutil
from pathlib import Path

import pytest

fz = pytest.importorskip("fz")

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "moret6"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")

FAKE = """#!/bin/bash
in="${@: -1}"
case "$PWD" in *,*) echo "FATAL:   container creation failed: mount hook function failure" >&2; exit 255 ;; esac
grep -q 'SPHE 8.7407' "$in" || { echo "radius not substituted" >&2; exit 0; }
grep -q 'mass (kg, 18.74 g/cm3): 52.42' "$in" || { echo "formula not evaluated" >&2; exit 0; }
cp '%(fix)s/ok_baseline.m6.listing' "$in.listing"
cp '%(fix)s/ok_baseline.m6.out.xml' "$in.out.xml"
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(ROOT / ".fz", tmp_path / ".fz")
    shutil.copy(ROOT / "examples" / "Moret" / "godiva.m6", tmp_path)
    fake = tmp_path / "bin" / "moret.py"
    fake.parent.mkdir()
    fake.write_text(FAKE % {"fix": FIXTURES / "ok_baseline"})
    fake.chmod(0o755)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("MORET_CMD", str(fake))
    monkeypatch.setenv("MORET_TMPDIR", str(scratch))
    monkeypatch.setenv("FZ_MAX_RETRIES", "1")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.parametrize("calculators", ["localhost_Moret", None])
def test_fzr(workspace, calculators):
    kwargs = {"calculators": calculators} if calculators else {}
    results = fz.fzr("godiva.m6", {"radius": [8.7407], "u5": 4.49988e-02}, "Moret",
                     results_dir=str(workspace / "results"), **kwargs)
    row = results.iloc[0]
    assert row["status"] == "done", row.to_dict()
    assert row["moret_status"] == "NORMAL END"
    assert float(row["mean_keff"]) == pytest.approx(0.99381)
    assert float(row["sigma_keff"]) == pytest.approx(0.00203)
    assert row["keff_estimator"] == "COMBI. GENERAL"
    assert list((workspace / "scratch").iterdir()) == []


def test_fzr_failed_case(workspace):
    """A run that produces no listing is reported as failed (Moret.sh exit code 5)."""
    results = fz.fzr("godiva.m6", {"radius": [9.0], "u5": 4.49988e-02}, "Moret",
                     calculators="localhost_Moret", results_dir=str(workspace / "results"))
    row = results.iloc[0]
    assert row["status"] != "done"
    assert row["moret_status"] == "NO OUTPUT"
