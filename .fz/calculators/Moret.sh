#!/bin/bash
# Moret calculator script for fz
#
# Runs MORET on the input dataset (.m6, .m5 or .moret) given by fz, then
# decides success from the MORET listing, not from the launcher exit code
# (MORET 6.0.0 and 5.D.1 launchers return 0 even on abnormal end or crash).
#
# Environment (all optional):
#   MORET_CMD      MORET launcher (default: moret.py on PATH, else /opt/MORET/scripts/moret.py)
#   MORET_RELEASE  release passed as first launcher argument
#                  (moret.py {5A1,5B1,5B2,5C1,5D1,6.0} input_file);
#                  default: 5D1 for .m5, 6.0 otherwise; set to "" for launchers
#                  taking only the input file (e.g. moret6.sh)
#   MORET_OPTS     extra launcher options, placed before the release (e.g. --keep_tmp_dir)
#   MORET_TMPDIR   where to run when the case directory contains "," or ":"
#                  (default: $TMPDIR, else /tmp); outputs are copied back
#
# The launcher output (stdout and stderr) is also written to moret.log, read by
# the Moret model to report the cause of a crash (e.g. "forrtl: severe (174): SIGSEGV").
#
# Exit codes:
#   0 normal end (NORMAL END OF THE CALCULATION, including the STOP option)
#   1 no input dataset          2 usage
#   4 launcher not found        5 no listing produced (launcher/environment failure)
#   6 abnormal end (MORET error, message on stderr)
#   7 listing without end banner (crash or interrupted run)

# Input: a directory, or the list of input files given by fz
if [ $# -eq 0 ]; then
  echo "Usage: $0 <input.m6|input.m5|input.moret ...|input_directory>" >&2
  exit 2
fi
if [ -d "$1" ]; then
  cd "$1" || exit 1
  set -- *
fi
INPUT=""
for f in "$@"; do
  case "$f" in
    *.m6) INPUT="$f"; break ;;
    *.m5|*.moret) [ -z "$INPUT" ] && INPUT="$f" ;;
  esac
done
if [ -z "$INPUT" ]; then
  echo "No MORET dataset (.m6, .m5 or .moret) found in: $*" >&2
  exit 1
fi

# Launcher
if [ -z "${MORET_CMD:-}" ]; then
  MORET_CMD="$(command -v moret.py || echo /opt/MORET/scripts/moret.py)"
fi
if [ ! -e "$MORET_CMD" ] && ! command -v "$MORET_CMD" >/dev/null 2>&1; then
  echo "MORET launcher not found: $MORET_CMD (set MORET_CMD)" >&2
  exit 4
fi
case "$INPUT" in
  *.m5) DEFAULT_RELEASE="5D1" ;;
  *)    DEFAULT_RELEASE="6.0" ;;
esac
RELEASE="${MORET_RELEASE-$DEFAULT_RELEASE}"

# Previous outputs would be mistaken for the new ones
rm -f "$INPUT.listing" "$INPUT.out.xml" "$INPUT.out.xml.gz" moret.log

# MORET 6 container scripts bind the dataset directory with
# "singularity --bind <dir>:/workdir,...": a "," or ":" in the path (fz names
# case directories "x=1,y=2") breaks the bind. Run in a temporary directory then.
case "$PWD" in
  *,*|*:*)
    RUN_DIR="$(mktemp -d "${MORET_TMPDIR:-${TMPDIR:-/tmp}}/fz-moret.XXXXXX")" || exit 5
    cp -p -- * "$RUN_DIR/" 2>/dev/null
    ;;
  *) RUN_DIR="" ;;
esac

if [ -n "$RUN_DIR" ]; then
  (cd "$RUN_DIR" && "$MORET_CMD" ${MORET_OPTS:-} $RELEASE "$INPUT") 2>&1 | tee moret.log
  RC=${PIPESTATUS[0]}
  # bring back what MORET produced (the input files are unchanged copies)
  cp -rp -- "$RUN_DIR"/. . && rm -rf -- "$RUN_DIR"
else
  "$MORET_CMD" ${MORET_OPTS:-} $RELEASE "$INPUT" 2>&1 | tee moret.log
  RC=${PIPESTATUS[0]}
fi

# Outputs are named <input>.listing / <input>.out.xml (verified MORET 6.0.0 and 5.D.1);
# <basename>.listing is accepted as a fallback for other releases.
LISTING="$INPUT.listing"
[ -f "$LISTING" ] || LISTING="${INPUT%.*}.listing"
if [ ! -f "$LISTING" ]; then
  echo "MORET produced no listing ($INPUT.listing); launcher exit code $RC" >&2
  grep -m1 -iE "command not found|commande introuvable|no such file|error" moret.log >&2
  echo "Check MORET_CMD, MORET_RELEASE and the launcher environment (e.g. singularity in PATH)." >&2
  exit 5
fi

# End banners are matched as framed lines ("|   ...   |"): the dataset echoed in the
# listing (":...:") and "NORMAL END FOR DATA READING" must not match
if grep -qE '^ *[|] +ABNORMAL END OF THE CALCULATION +[|]' "$LISTING"; then
  echo "MORET abnormal end ($LISTING):" >&2
  awk '/^Error message number /{p=1} p && /^[ \t]*$/{exit} p' "$LISTING" | head -30 >&2
  exit 6
fi
if ! grep -qE '^ *[|] +NORMAL END OF THE CALCULATION +[|]' "$LISTING"; then
  echo "MORET listing has no end banner, crash or interrupted run ($LISTING); launcher exit code $RC" >&2
  grep -m1 -E "forrtl: |[Ss]egmentation fault|SIGSEGV|Aborted|Killed" moret.log >&2
  exit 7
fi

if grep -qE '^ *[|] +STOP OPTION +[|]' "$LISTING"; then
  echo "MORET normal end with the STOP option: no simulation, no keff" >&2
fi
[ "$RC" -ne 0 ] && echo "Warning: MORET normal end but launcher exit code $RC" >&2
exit 0
