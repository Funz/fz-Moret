"""Output extraction of the Moret model, in plain Python (regular expressions).

Each public function takes the case output directory and returns one output
value (None when absent). tools/make_model.py embeds the source of each
function, with the private helpers, in a ``python://`` output of
.fz/models/Moret.json: this module must stay self-contained (standard library
only) and the functions must not use names defined outside them, except the
private helpers and module-level constants below.

Formats (verified on MORET 6.0.0 builds d9ff307 / 052de83 and MORET 5.D.1,
see tests/moret_probe/README.md):
- <input>.listing: always written; the dataset is echoed with each line
  wrapped in ":" (":GEOM:"), end banners are framed lines ("|  ...  |");
- <input>.out.xml, or <input>.out.xml.gz with OUTP XMLZ 1;
- moret.log: launcher stdout + stderr, written by Moret.sh (crash cause);
  fz's err.txt / out.txt are read as a fallback.
"""

import gzip
import re
from pathlib import Path

# "##   CYCLE    100 LOWEST SIGMA ESTI.   0.99381 +/-  0.00203  : ..." (also used
# for the dkeff of each perturbed system, in signed scientific notation)
LOWEST = re.compile(r"^##.*\bCYCLE\s+(\d+)\s+LOWEST SIGMA ESTI\.\s+(\S+)\s+\+/-\s+(\S+)")
# "##       COMBI. GENERAL            0.99381 +/-  0.00203  : ..."
ESTIMATOR = re.compile(r"^##\s+(\S.*?)\s+(\S+)\s+\+/-\s+(\S+)\s+:")
BANNER = r"^\s*\|\s+{}\s+\|"
CRASH = re.compile(r"forrtl: |[Ss]egmentation fault|SIGSEGV|Aborted|Killed"
                   r"|command not found|commande introuvable")


def _listing(d):
    """Listing of the MORET dataset (apo2.listing: APOLLO2 step of moret.py)."""
    files = sorted(p for p in Path(d).glob("*.listing") if p.name != "apo2.listing")
    return files[0] if files else None


def _lines(path):
    return Path(path).read_bytes().decode("latin-1").splitlines()


def _final_keff(d):
    """(active cycles, keff, sigma) of the first LOWEST SIGMA line, with its line index."""
    listing = _listing(d)
    if listing is None:
        return None, None
    lines = _lines(listing)
    for i, line in enumerate(lines):
        m = LOWEST.match(line)
        if m:
            return m.groups(), lines[i + 1:]
    return None, None


def moret_status(d):
    """NORMAL END [(STOP OPTION, NO SIMULATION)] | ABNORMAL END: <error> |
    NO END BANNER[: <error>][: <crash cause>] | NO OUTPUT"""
    listing = _listing(d)
    if listing is None:
        return "NO OUTPUT"
    message, n, reading, done = [], 0, False, False
    abnormal = normal = stop = False
    for line in _lines(listing):
        if not done and line.startswith("Error message number "):
            reading = True
        if reading:
            if not line.strip():
                reading, done = False, True
                continue
            if n < 5:
                message.append(" ".join(line.split()))
            n += 1
            if "expected keyword" in line:
                reading, done = False, True
            continue
        if re.match(BANNER.format("ABNORMAL END OF THE CALCULATION"), line):
            abnormal = True
        elif re.match(BANNER.format("NORMAL END OF THE CALCULATION"), line):
            normal = True
        elif re.match(BANNER.format("STOP OPTION"), line):
            stop = True
    error = re.sub(r":$", ".", " ".join(message))
    if abnormal:
        return "ABNORMAL END" + (": " + error if error else "")
    if normal:
        return "NORMAL END (STOP OPTION, NO SIMULATION)" if stop else "NORMAL END"
    status = "NO END BANNER" + (": " + error if error else "")
    for name in ("moret.log", "err.txt", "out.txt"):
        log = Path(d) / name
        if log.is_file():
            crash = [" ".join(l.split()) for l in _lines(log) if CRASH.search(l)]
            if crash:
                return status + ": " + crash[0]
    return status


def mean_keff(d):
    """keff of the lowest-sigma estimator (initial system)."""
    final, _ = _final_keff(d)
    return float(final[1]) if final else None


def sigma_keff(d):
    """Standard deviation of the lowest-sigma estimator (initial system)."""
    final, _ = _final_keff(d)
    return float(final[2]) if final else None


def active_cycles(d):
    """Number of active cycles of the final keff estimate."""
    final, _ = _final_keff(d)
    return int(final[0]) if final else None


def keff_estimator(d):
    """Name of the lowest-sigma estimator (e.g. COMBI. GENERAL)."""
    final, rest = _final_keff(d)
    if not final:
        return None
    for line in rest:
        m = ESTIMATOR.match(line)
        if m and m.group(2) == final[1] and m.group(3) == final[2]:
            return m.group(1)
    return None


def transient_cycles(d):
    """Greatest number of initial active cycles to suppress for the stationarity
    of every estimator (first row of the MORET table)."""
    listing = _listing(d)
    if listing is None:
        return None
    found = False
    for line in _lines(listing):
        if "SUPPRESSION OF THE GREATEST NUMBER OF CYCLES" in line:
            found = True
        elif found:
            m = re.match(r"^\s*\|\s+(\d+)\s", line)
            if m:
                return int(m.group(1))
    return None


def _perturbations(d):
    """{system: (dkeff, sigma)}: correlated sampling (PERTURBED SYSTEM NO n block,
    LOWEST SIGMA line) or Taylor series (one "##  n  dk +/- s" line per system)."""
    listing = _listing(d)
    result = {}
    if listing is None:
        return result
    system, taylor = 0, False
    for line in _lines(listing):
        if not line.startswith("##"):
            continue
        m = re.search(r"PERTURBED SYSTEM NO +(\d+)", line)
        if m:
            system = int(m.group(1))
        elif system:
            m = LOWEST.match(line)
            if m:
                result[system] = (float(m.group(2)), float(m.group(3)))
                system = 0
        if "TAYLOR SERIES EXPANSION" in line:
            taylor = True
        f = line.split()
        if taylor and len(f) > 4 and f[1].isdigit() and f[3] == "+/-":
            result[int(f[1])] = (float(f[2]), float(f[4]))
    return result


def dkeff(d):
    """keff variation of each perturbed system, {"1": ..., "2": ...} (flattened by fz)."""
    pert = _perturbations(d)
    return {str(k): pert[k][0] for k in sorted(pert)}


def sigma_dkeff(d):
    """Standard deviation of the keff variation of each perturbed system."""
    pert = _perturbations(d)
    return {str(k): pert[k][1] for k in sorted(pert)}


def moret_warnings(d):
    """Information messages, e.g. "WARN_GEOM 14 (x2), WARN_GEOM 16, WARN_ACE_DATA 2"."""
    listing = _listing(d)
    if listing is None:
        return None
    counts = {}
    for line in _lines(listing):
        m = re.match(r"^Information message number (\d+) from (WARN_\w+)", line)
        if m:
            key = m.group(2) + " " + m.group(1)
            counts[key] = counts.get(key, 0) + 1
    return ", ".join(k + (" (x%d)" % n if n > 1 else "") for k, n in counts.items()) or None


def moret_version(d):
    """e.g. "MORET 6.0.0 (commit short hash: 052de83)" (banner of the listing)."""
    listing = _listing(d)
    if listing is None:
        return None
    for line in _lines(listing):
        m = re.search(r"<<<<<<< (.*?) >>>>>>>", line)
        if m:
            return m.group(1)
    return None


def cpu_time(d):
    """Global CPU time (s): out.xml[.gz] <cpu_time><global>, else the listing."""
    xml = sorted(Path(d).glob("*.out.xml")) + sorted(Path(d).glob("*.out.xml.gz"))
    if xml:
        data = xml[0].read_bytes()
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        m = re.search(r"<cpu_time>.*?<global>\s*(\S+?)\s*</global>",
                      data.decode("latin-1"), re.S)
        if m:
            return float(m.group(1))
    listing = _listing(d)
    if listing is not None:
        for line in _lines(listing):
            m = re.match(r"^global\s+:\s+(\S+)", line)
            if m:
                return float(m.group(1))
    return None


OUTPUTS = ["moret_status", "mean_keff", "sigma_keff", "keff_estimator", "active_cycles",
           "transient_cycles", "dkeff", "sigma_dkeff", "moret_warnings", "moret_version",
           "cpu_time"]
