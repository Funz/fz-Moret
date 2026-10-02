"""Output extraction of the Moret model against real MORET 6.0.0 outputs.

Fixtures in tests/fixtures/moret6/ come from tests/moret_probe (run of
2026-10-01, MORET 6.0.0, JEFF-3.1.1; host and user names anonymized).

Run: pytest tests/test_outputs_moret6.py
"""

import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

fz = pytest.importorskip("fz")

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "moret6"
MODEL = json.loads((ROOT / ".fz" / "models" / "Moret.json").read_text())


def outputs(case):
    """Run the model output commands on one fixture directory."""
    df = fz.fzo(str(FIXTURES / case), MODEL)
    return df.iloc[0].to_dict()


def missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


# --- Ground truth read directly from out.xml (independent of the model) ---

def test_fixture_out_xml_matches_listing():
    root = ET.parse(FIXTURES / "ok_baseline" / "ok_baseline.m6.out.xml").getroot()
    assert root.tag == "calculation"
    assert root.findtext("end_message") == "NORMAL END"
    estis = {e.get("name"): e for e in root.find("keff").findall("esti")}
    # first value of each vector = no initial cycle suppressed
    best = min(estis.values(), key=lambda e: float(e.findtext("std").split()[0]))
    assert best.get("name") == "COMBI. GENERAL"
    assert float(best.findtext("mean").split()[0]) == pytest.approx(0.99381, abs=1e-5)
    assert float(best.findtext("std").split()[0]) == pytest.approx(0.00203, abs=1e-5)


def test_fixture_error_out_xml():
    root = ET.parse(FIXTURES / "err_xmlc" / "err_xmlc.m6.out.xml").getroot()
    assert root.findtext("end_message") == "ABNORMAL END"
    assert "Error message number 20" in "".join(root.find("error_message").itertext())


# --- Current model behaviour ---

def test_mean_and_sigma_keff_baseline():
    out = outputs("ok_baseline")
    assert float(out["mean_keff"]) == pytest.approx(0.99381, abs=1e-5)
    assert float(out["sigma_keff"]) == pytest.approx(0.00203, abs=1e-5)


def test_no_keff_on_abnormal_end():
    out = outputs("err_xmlc")
    assert missing(out["mean_keff"])
    assert missing(out["sigma_keff"])


def test_status_normal_end():
    assert outputs("ok_baseline")["moret_status"] == "NORMAL END"


@pytest.mark.parametrize("case,number,text", [
    ("err_xmlc", 20, "The XMLC keyword is no longer available."),
    ("err_medium_mismatch", 3, "The medium name FOO does not match a material composition name."),
])
def test_status_abnormal_end_with_error(case, number, text):
    status = outputs(case)["moret_status"]
    assert status.startswith("ABNORMAL END: ")
    assert f"Error message number {number} " in status
    assert status.endswith(text)


def test_status_from_listing_when_no_out_xml(tmp_path):
    shutil.copy(FIXTURES / "err_xmlc" / "err_xmlc.m6.listing", tmp_path)
    status = fz.fzo(str(tmp_path), MODEL).iloc[0]["moret_status"]
    assert status.startswith("ABNORMAL END: Error message number 20 ")


def test_status_no_output(tmp_path):
    (tmp_path / "godiva.m6").write_text("input only\n")
    assert fz.fzo(str(tmp_path), MODEL).iloc[0]["moret_status"] == "NO OUTPUT"


def test_no_dkeff_without_perturbation():
    out = outputs("ok_baseline")
    assert not any(k.startswith(("dkeff", "sigma_dkeff")) for k in out)


def test_dkeff_repl():
    out = outputs("ok_pert_repl_count")
    assert out["dkeff_1"] == pytest.approx(8.0230e-03, rel=1e-4)
    assert out["sigma_dkeff_1"] == pytest.approx(4.6602e-05, rel=1e-4)
    assert out["dkeff_2"] == pytest.approx(-8.0694e-03, rel=1e-4)
    assert out["sigma_dkeff_2"] == pytest.approx(4.6067e-05, rel=1e-4)


def test_dkeff_tayl():
    out = outputs("ok_pert_tayl")
    assert float(out["mean_keff"]) == pytest.approx(0.99848, abs=1e-5)
    assert out["dkeff_1"] == pytest.approx(8.0852e-03, rel=1e-4)
    assert out["sigma_dkeff_1"] == pytest.approx(1.4409e-04, rel=1e-4)
    assert out["dkeff_2"] == pytest.approx(2.6013e-04, rel=1e-4)


def test_dkeff_matches_out_xml():
    root = ET.parse(FIXTURES / "ok_pert_repl_count" / "ok_pert_repl_count.m6.out.xml").getroot()
    out = outputs("ok_pert_repl_count")
    for system in root.find("perturbations/dkeff").findall("perturbed_system"):
        esti = system.find("esti[@name='COMBI. GENERAL']")
        num = system.get("num")
        assert out[f"dkeff_{num}"] == pytest.approx(float(esti.findtext("mean")), rel=1e-4)
