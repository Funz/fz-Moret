"""Tests of .fz/calculators/Moret.sh with a fake MORET launcher.

The fake launcher mimics the verified behaviour of moret.py (MORET 6.0.0):
release as first argument, outputs named <input>.listing / <input>.out.xml,
exit code 0 whatever the outcome. It replays the reference outputs of
tests/fixtures/moret6 and records its arguments.

Run: pytest tests/test_calculator.py
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".fz" / "calculators" / "Moret.sh"
FIXTURES = ROOT / "tests" / "fixtures" / "moret6"

FAKE = """#!/bin/bash
echo "$@" > "$(dirname "$0")/args.txt"
in="${@: -1}"
case "$FAKE_CASE" in
  none) exit 0 ;;
  truncated) head -n 100 "$FIXTURES/ok_baseline/ok_baseline.m6.listing" > "$in.listing"; exit 0 ;;
  *) cp "$FIXTURES/$FAKE_CASE/$FAKE_CASE.m6.listing" "$in.listing"
     cp "$FIXTURES/$FAKE_CASE/$FAKE_CASE.m6.out.xml" "$in.out.xml"; exit 0 ;;
esac
"""


@pytest.fixture
def run(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "moret.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    case_dir = tmp_path / "case"
    case_dir.mkdir()

    def _run(fake_case="ok_baseline", input_name="godiva.m6", env=None, args=None):
        (case_dir / input_name).write_text("dataset\n")
        full_env = dict(os.environ, MORET_CMD=str(fake), FAKE_CASE=fake_case,
                        FIXTURES=str(FIXTURES))
        full_env.pop("MORET_RELEASE", None)
        full_env.update(env or {})
        proc = subprocess.run(["bash", str(SCRIPT)] + (args or [input_name]),
                              cwd=case_dir, env=full_env, capture_output=True, text=True)
        launcher_args = (bindir / "args.txt").read_text().split() if (bindir / "args.txt").exists() else None
        return proc, launcher_args

    return _run


def test_normal_end(run):
    proc, args = run("ok_baseline")
    assert proc.returncode == 0, proc.stderr
    assert args == ["6.0", "godiva.m6"]


def test_abnormal_end_reports_error(run):
    proc, _ = run("err_xmlc")
    assert proc.returncode == 6
    assert "Error message number 20" in proc.stderr
    assert "The XMLC keyword is no longer available." in proc.stderr


def test_no_listing(run):
    proc, _ = run("none")
    assert proc.returncode == 5
    assert "no listing" in proc.stderr


def test_listing_without_banner(run):
    proc, _ = run("truncated")
    assert proc.returncode == 7


def test_release_default_m5(run):
    _, args = run("ok_baseline", input_name="godiva.m5")
    assert args == ["5D1", "godiva.m5"]


def test_release_override_and_options(run):
    _, args = run(env={"MORET_RELEASE": "5C1", "MORET_OPTS": "--keep_tmp_dir"})
    assert args == ["--keep_tmp_dir", "5C1", "godiva.m6"]


def test_release_empty_means_no_argument(run):
    _, args = run(env={"MORET_RELEASE": ""})
    assert args == ["godiva.m6"]


def test_m6_preferred_over_m5(run, tmp_path):
    (tmp_path / "case" / "old.m5").write_text("x\n")
    _, args = run(args=["old.m5", "godiva.m6"])
    assert args[-1] == "godiva.m6"


def test_directory_argument(run):
    proc, args = run(args=["."])
    assert proc.returncode == 0, proc.stderr
    assert args[-1] == "godiva.m6"


def test_no_dataset(run, tmp_path):
    proc = subprocess.run(["bash", str(SCRIPT), "notes.txt"], cwd=tmp_path,
                          capture_output=True, text=True)
    assert proc.returncode == 1


def test_launcher_not_found(tmp_path):
    (tmp_path / "godiva.m6").write_text("x\n")
    env = dict(os.environ, MORET_CMD=str(tmp_path / "missing.py"))
    proc = subprocess.run(["bash", str(SCRIPT), "godiva.m6"], cwd=tmp_path, env=env,
                          capture_output=True, text=True)
    assert proc.returncode == 4


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_script_syntax():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
