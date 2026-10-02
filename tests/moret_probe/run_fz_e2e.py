#!/usr/bin/env python3
"""End-to-end test of the plugin through fz with a real MORET.

Run from the repository root:
    MORET_CMD=/path/to/moret.py MORET_RELEASE=6.0 python3 tests/moret_probe/run_fz_e2e.py

Runs examples/Moret/godiva.m6 (radius 8.5 / 8.7407 / 9.0) with the
localhost_Moret calculator (.fz/calculators/Moret.sh), which reads MORET_CMD,
MORET_RELEASE and MORET_OPTS from the environment.

Results: tests/moret_probe/results-fz-e2e/ (case directories + results.csv/.txt)
"""

import os
import shutil
import sys
from pathlib import Path

import fz

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "moret_probe" / "results-fz-e2e"
RELEASE = os.environ.get("MORET_RELEASE", "6.0")

if __name__ == "__main__":
    os.chdir(ROOT)
    if (RELEASE.startswith("6") and not shutil.which("singularity")
            and not os.environ.get("MORET_SKIP_ENV_CHECK")):
        sys.exit("singularity not in PATH: MORET 6 cannot start "
                 "(load the module, or set MORET_SKIP_ENV_CHECK=1)")
    if OUT.exists():
        shutil.rmtree(OUT)
    results = fz.fzr(
        "examples/Moret/godiva.m6",
        {"radius": [8.5, 8.7407, 9.0], "u5": 4.49988e-02},
        "Moret",
        calculators="localhost_Moret",
        results_dir=str(OUT),
    )
    results.to_csv(OUT / "results.csv", index=False)
    (OUT / "results.txt").write_text(results.T.to_string())
    print(results[["radius", "status", "moret_status", "mean_keff", "sigma_keff"]].to_string())
    print(f"Results: {OUT}")
