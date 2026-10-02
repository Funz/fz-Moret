#!/usr/bin/env python3
"""Synthese des resultats produits par run_probe.sh.

Usage : python3 summarize.py results-<label>-<date>/

Pour chaque cas : code retour, fichiers produits, marqueur de fin normale,
messages d'erreur MORET, lignes keff candidates. Aucune hypothese sur le
format n'est imposee : les motifs sont volontairement larges, le but est de
les consolider a partir des sorties reelles.
"""

import re
import sys
from pathlib import Path

MARKERS = {
    "normal_end": re.compile(r"NORMAL END|FIN NORMALE", re.I),
    "error": re.compile(r"Error message number|ERROR_[A-Z_]+|ERREUR", re.I),
    "keff_line": re.compile(r"(FAIBLE|LOWEST)\s+SIGMA|KEFF.*\+/-", re.I),
    "pert": re.compile(r"PERT|DELTA|SENSI|TAYL", re.I),
    "supp": re.compile(r"TRANSIENT|TRANSITOIRE|STATIONAR|SUPP", re.I),
}
TEXT_EXT = {"", ".txt", ".listing", ".xml", ".out", ".log", ".keff"}


def text_files(case_dir):
    for p in sorted(case_dir.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix in (".m5", ".m6"):
            continue
        if p.suffix.lower() in TEXT_EXT or p.stat().st_size < 5_000_000:
            yield p


def scan(case_dir):
    hits = {k: [] for k in MARKERS}
    for p in text_files(case_dir):
        try:
            content = p.read_text(errors="replace")
        except OSError:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            for key, rx in MARKERS.items():
                if rx.search(line) and len(hits[key]) < 6:
                    hits[key].append(f"{p.relative_to(case_dir)}:{i}: {line.strip()[:160]}")
    return hits


def main(results_dir):
    root = Path(results_dir)
    for case_dir in sorted(d for d in root.iterdir() if d.is_dir()):
        rc = (case_dir / ".exit_code").read_text().strip() if (case_dir / ".exit_code").exists() else "?"
        dur = (case_dir / ".duration_s").read_text().strip() if (case_dir / ".duration_s").exists() else "?"
        produced = []
        if (case_dir / ".files_after").exists():
            for line in (case_dir / ".files_after").read_text().splitlines():
                parts = line.split(None, 2)
                if len(parts) == 3 and not Path(parts[2]).name.startswith("."):
                    produced.append(f"{parts[0]} {parts[1].strip():>10} {parts[2]}")
        hits = scan(case_dir)
        print("=" * 100)
        print(f"{case_dir.name}   rc={rc}   duree={dur}s")
        print("  fichiers :")
        for f in produced:
            print(f"    {f}")
        for key, lines in hits.items():
            if lines:
                print(f"  [{key}]")
                for line in lines:
                    print(f"    {line}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
