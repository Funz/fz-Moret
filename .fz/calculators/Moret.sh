#!/bin/bash
# Moret calculator script for fz
#
# Runs MORET on the input dataset (.m6, or .m5 for MORET 5) given by fz, then
# decides success from the MORET outputs, not from the launcher exit code
# (MORET 6.0.0 launchers were observed to return 0 even on abnormal end).
#
# Environment (all optional):
#   MORET_CMD      MORET launcher (default: moret.py on PATH, else /opt/MORET/scripts/moret.py)
#   MORET_RELEASE  release passed as first launcher argument
#                  (moret.py {5A1,5B1,5B2,5C1,5D1,6.0} input_file);
#                  default: 6.0 for .m6, 5D1 for .m5; set to "" for launchers without it
#   MORET_OPTS     extra launcher options, placed before the release (e.g. --keep_tmp_dir)
#
# Exit codes:
#   0 normal end (NORMAL END OF THE CALCULATION)
#   1 no input dataset          2 usage
#   4 launcher not found        5 no listing produced (launcher/environment failure)
#   6 abnormal end (MORET error, message on stderr)
#   7 listing without end banner (interrupted run)

# Input: a directory, or the list of input files given by fz
if [ $# -eq 0 ]; then
  echo "Usage: $0 <input.m6|input.m5 ...|input_directory>" >&2
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
    *.m5) [ -z "$INPUT" ] && INPUT="$f" ;;
  esac
done
if [ -z "$INPUT" ]; then
  echo "No MORET dataset (.m6 or .m5) found in: $*" >&2
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
  *.m6) DEFAULT_RELEASE="6.0" ;;
  *)    DEFAULT_RELEASE="5D1" ;;
esac
RELEASE="${MORET_RELEASE-$DEFAULT_RELEASE}"

# Previous outputs would be mistaken for the new ones
rm -f "$INPUT.listing" "$INPUT.out.xml"

"$MORET_CMD" ${MORET_OPTS:-} $RELEASE "$INPUT"
RC=$?

# Outputs are named <input>.listing / <input>.out.xml (verified MORET 6.0.0);
# <basename>.listing is accepted as a fallback for other releases.
LISTING="$INPUT.listing"
[ -f "$LISTING" ] || LISTING="${INPUT%.*}.listing"
if [ ! -f "$LISTING" ]; then
  echo "MORET produced no listing ($INPUT.listing); launcher exit code $RC" >&2
  echo "Check MORET_CMD, MORET_RELEASE and the launcher environment (e.g. singularity in PATH)." >&2
  exit 5
fi

# Full banners only: "NORMAL END" alone also matches "ABNORMAL END ..." and
# "NORMAL END FOR DATA READING"
if grep -q "ABNORMAL END OF THE CALCULATION" "$LISTING"; then
  echo "MORET abnormal end ($LISTING):" >&2
  grep -A3 "^Error message number" "$LISTING" | grep -v '^\s*$' >&2
  exit 6
fi
if ! grep -q "NORMAL END OF THE CALCULATION" "$LISTING"; then
  echo "MORET listing has no end banner, run interrupted? ($LISTING); launcher exit code $RC" >&2
  exit 7
fi

[ "$RC" -ne 0 ] && echo "Warning: MORET normal end but launcher exit code $RC" >&2
exit 0
