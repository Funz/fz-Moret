"""Output extraction of the Moret model against real MORET outputs.

Fixtures (tests/fixtures/README.md) come from tests/moret_probe runs, JEFF-3.1.1,
host and user names anonymized:
- moret6/: MORET 6.0.0, builds d9ff307 (2026-10-01) and 052de83 (2026-10-15);
- moret5/: MORET 5.D.1 (2026-10-15).

Run: pytest tests/test_outputs.py
"""

import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

fz = pytest.importorskip("fz")
# python:// outputs of the Moret model need fz >= 1.2
pytest.importorskip("fz.outparsers", reason="fz >= 1.2 required (python:// outputs)")

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "moret6"
FIXTURES5 = ROOT / "tests" / "fixtures" / "moret5"
MODEL = json.loads((ROOT / ".fz" / "models" / "Moret.json").read_text())


def outputs(case, fixtures=FIXTURES):
    """Run the model output commands on one fixture directory."""
    df = fz.fzo(str(fixtures / case), MODEL)
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


def test_dkeff_vard():
    """VARD 0.01 -0.01 (no count): same dkeff as a +1 % density REPL (probe H33b)."""
    out = outputs("ok_pert_vard")
    assert out["dkeff_1"] == pytest.approx(8.2643e-03, rel=1e-4)
    assert out["dkeff_2"] == pytest.approx(-8.3131e-03, rel=1e-4)
    assert "dkeff_3" not in out


# --- Status: banners, error message, crash, STOP ---

def test_status_error_message_truncated():
    """Syntax errors are followed by the whole grammar: keep up to "expected keywords"."""
    status = outputs("err_syntax_line")["moret_status"]
    assert status.startswith("ABNORMAL END: Error message number 1 from ERROR_READING_DATA")
    assert status.endswith('The word "Ceci" is not one of the expected keywords.')
    assert "GEOM ... ENDG" not in status


def test_status_stop_option():
    out = outputs("var_stop")
    assert out["moret_status"] == "NORMAL END (STOP OPTION, NO SIMULATION)"
    assert missing(out["mean_keff"])


def test_status_crash_after_results():
    """Perturbed system identical to the initial one: keff and dkeff printed, then
    'forrtl: error (73): floating divide by zero' and no end banner (probe H36)."""
    out = outputs("var_pert_identical_system")
    assert out["moret_status"] == "NO END BANNER: forrtl: error (73): floating divide by zero"
    assert float(out["mean_keff"]) == pytest.approx(1.05662, abs=1e-5)
    assert out["dkeff_2"] == 0


def test_status_crash_without_message():
    """Undefined container volume: SIGSEGV with build 052de83, no error message (probe H34)."""
    out = outputs("err_missing_container")
    assert out["moret_status"] == "NO END BANNER: forrtl: severe (174): SIGSEGV, segmentation fault occurred"


def test_status_crash_reason_from_fz_stderr(tmp_path):
    """Without moret.log, the crash reason is looked for in fz's err.txt / out.txt."""
    case = FIXTURES / "var_pert_identical_system"
    shutil.copy(case / "var_pert_identical_system.m6.listing", tmp_path)
    shutil.copy(case / "moret.log", tmp_path / "err.txt")
    assert fz.fzo(str(tmp_path), MODEL).iloc[0]["moret_status"].endswith("floating divide by zero")


def test_status_ignores_echoed_dataset(tmp_path):
    """The dataset echo (":...:") and NORMAL END FOR DATA READING are not end banners."""
    listing = (FIXTURES / "ok_baseline" / "ok_baseline.m6.listing").read_text(encoding="latin-1")
    cut = listing.index("FINAL KEFF ESTIMATE")
    (tmp_path / "x.m6.listing").write_text(
        ":* NORMAL END OF THE CALCULATION:\n:* | ABNORMAL END OF THE CALCULATION |:\n" + listing[:cut],
        encoding="latin-1")
    assert fz.fzo(str(tmp_path), MODEL).iloc[0]["moret_status"] == "NO END BANNER"


def test_status_apo2_listing_ignored(tmp_path):
    """moret.py copies apo2.listing next to the MORET listing (APOLLO2 coupling)."""
    shutil.copy(FIXTURES / "ok_baseline" / "ok_baseline.m6.listing", tmp_path)
    (tmp_path / "apo2.listing").write_text("APOLLO2 listing\n")
    out = fz.fzo(str(tmp_path), MODEL).iloc[0]
    assert out["moret_status"] == "NORMAL END"
    assert float(out["mean_keff"]) == pytest.approx(0.99381, abs=1e-5)


# --- Additional outputs ---

def test_keff_estimator_cycles_version():
    out = outputs("ok_baseline")
    assert out["keff_estimator"] == "COMBI. GENERAL"
    assert int(out["active_cycles"]) == 100
    assert int(out["transient_cycles"]) == 8
    assert out["moret_version"] == "MORET 6.0.0 (commit short hash: d9ff307)"
    assert float(out["cpu_time"]) > 0


def test_active_cycles_with_sigma_termination():
    """TERM KEFF SIGM 0.003 stops after 29 active cycles (probe H25)."""
    out = outputs("ok_term_sigm")
    assert int(out["active_cycles"]) == 29
    assert float(out["sigma_keff"]) == pytest.approx(0.003)


def test_warnings_lattice_exceeding_container():
    """A lattice larger than its container is truncated silently: only WARN_GEOM 16 (probe H35)."""
    out = outputs("var_lattice_exceed")
    assert "WARN_GEOM 16" in out["moret_warnings"]
    assert "WARN_GEOM 14 (x2)" in out["moret_warnings"]
    assert "WARN_GEOM" not in outputs("ok_baseline")["moret_warnings"]


def test_compressed_out_xml():
    """OUTP XMLZ 1: <input>.out.xml.gz (kept by moret6.sh, not copied back by moret.py)."""
    out = outputs("var_xmlz")
    assert out["moret_status"] == "NORMAL END"
    assert float(out["cpu_time"]) == pytest.approx(2.98038, rel=1e-4)


def test_cpu_time_from_listing_without_out_xml(tmp_path):
    shutil.copy(FIXTURES / "ok_term_sigm" / "ok_term_sigm.m6.listing", tmp_path)
    assert float(fz.fzo(str(tmp_path), MODEL).iloc[0]["cpu_time"]) == pytest.approx(3.1)


# --- MORET 5.D.1 ---

def test_moret5_repl():
    out = outputs("m5_pert_repl", FIXTURES5)
    assert out["moret_status"] == "NORMAL END"
    assert float(out["mean_keff"]) == pytest.approx(0.99607, abs=1e-5)
    assert out["dkeff_1"] == pytest.approx(7.9367e-03, rel=1e-4)
    assert out["sigma_dkeff_2"] == pytest.approx(4.5042e-05, rel=1e-4)
    assert out["moret_version"].startswith("MORET 5.D.1")
    assert out["keff_estimator"] == "COMBI. GENERAL"


def test_moret5_tayl():
    """Columns = perturbed systems: system 2 = U235 -1 % and density +1 % (probe H20/H32c)."""
    out = outputs("m5_pert_tayl", FIXTURES5)
    assert out["dkeff_1"] == pytest.approx(8.014e-03, rel=1e-4)
    assert out["dkeff_2"] == pytest.approx(2.6386e-04, rel=1e-4)


def test_moret5_abnormal_end():
    status = outputs("err_xmlc", FIXTURES5)["moret_status"]
    assert status.startswith("ABNORMAL END: Error message number 1 from ERROR_READING_INPUT")
