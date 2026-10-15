# Reference MORET outputs

Real outputs of the cases of `tests/moret_probe/cases` (same names), JEFF-3.1.1,
used by `tests/test_outputs.py`, `tests/test_calculator.py` and `tests/test_fz_e2e.py`.
Not hand-written: only anonymized (host and user names, developer and build host names,
site paths replaced by `/opt/moret/...` and `/work/...`).

| Directory | Code | Cases |
|---|---|---|
| `moret6/` | MORET 6.0.0 build d9ff307 (`moret.py 6.0`), 2026-10-01 | `ok_baseline`, `ok_pert_repl_count`, `ok_pert_tayl`, `err_xmlc`, `err_medium_mismatch`, `err_syntax_line` |
| `moret6/` | MORET 6.0.0 build 052de83 (container script, no release argument), 2026-10-15 | `var_stop`, `ok_term_sigm`, `var_xmlz` (`.out.xml.gz`), `var_lattice_exceed`, `ok_pert_vard`, `err_missing_container` (SIGSEGV), `var_pert_identical_system` (crash after results) |
| `moret5/` | MORET 5.D.1 (`moret.py 5D1`), 2026-10-15 | `m5_pert_repl`, `m5_pert_tayl`, `err_xmlc` (MORET 6 dataset rejected) |

`moret.log` = launcher stdout + stderr (as written by `Moret.sh`), kept for the crash cases.
