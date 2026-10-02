#!/bin/bash
# Lance chaque cas de tests/moret_probe/cases avec un MORET reel et archive
# tout ce qui est produit, pour consolider les hypotheses du plugin.
#
# Usage :
#   MORET_CMD=/chemin/vers/moret.py MORET_RELEASE=6.0 ./run_probe.sh [motif]
#   MORET_RELEASE=6.0               : version passee en 1er argument au lanceur
#                                     (moret.py {5A1,5B1,5B2,5C1,5D1,6.0} input_file) ;
#                                     vide = lanceur sans argument de version
#   MORET_OPTS=--keep_tmp_dir       : options supplementaires du lanceur (avant la version)
#   MORET_SKIP_ENV_CHECK=1          : ne pas verifier la presence de singularity
#   MORET_LIBR=ma_bibliotheque.xml  : remplace jeff311.xml dans les cas
#   MORET_LABEL=moret6              : suffixe de l archive (ex. moret5 / moret6)
#   motif                           : filtre glob sur les noms de cas (defaut *)

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
MORET_CMD="${MORET_CMD:-/opt/MORET/scripts/moret.py}"
RELEASE="${MORET_RELEASE-6.0}"
OPTS="${MORET_OPTS:-}"
LABEL="${MORET_LABEL:-moret${RELEASE}}"
PATTERN="${1:-*}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$HERE/results-$LABEL-$STAMP"
MAX_SIZE=$((20 * 1024 * 1024))  # fichiers plus gros non archives (liste seulement)

if [ ! -e "$MORET_CMD" ] && ! command -v "$MORET_CMD" >/dev/null 2>&1; then
  echo "MORET introuvable : $MORET_CMD (definir MORET_CMD)" >&2
  exit 1
fi

# MORET 6 s'execute dans un conteneur Singularity/Apptainer (constate le 2026-10-01)
# (verification desactivable : MORET_SKIP_ENV_CHECK=1)
if [ -z "${MORET_SKIP_ENV_CHECK:-}" ] && [ "${RELEASE#6}" != "$RELEASE" ] \
   && ! command -v singularity >/dev/null 2>&1; then
  echo "singularity absent du PATH : MORET $RELEASE ne pourra pas demarrer" >&2
  echo "(charger le module correspondant, ex. 'module load singularity', puis relancer)" >&2
  exit 1
fi

# Au moins un cas doit correspondre au motif
shopt -s nullglob
MATCHES=( "$HERE"/cases/$PATTERN.m5 "$HERE"/cases/$PATTERN.m6 )
shopt -u nullglob
if [ ${#MATCHES[@]} -eq 0 ]; then
  echo "Aucun cas ne correspond au motif '$PATTERN' dans $HERE/cases" >&2
  echo "(archive de sondes trop ancienne ? cas disponibles : $(ls "$HERE"/cases | tr '\n' ' '))" >&2
  exit 1
fi

mkdir -p "$OUT"

# Informations sur l environnement et le lanceur (H13 : commande de version)
{
  echo "date: $(date -Iseconds)"
  echo "uname: $(uname -a)"
  echo "MORET_CMD: $MORET_CMD"
  echo "MORET_RELEASE: ${RELEASE:-<aucun>}"
  echo "MORET_OPTS: ${OPTS:-<aucune>}"
  echo "singularity: $(command -v singularity || echo absent)  apptainer: $(command -v apptainer || echo absent)"
  echo "MORET_LIBR: ${MORET_LIBR:-<non defini, jeff311.xml>}"
  for opt in --version -version -v --help -h; do
    echo "===== $MORET_CMD $opt (rc ci-dessous)"
    timeout 30 "$MORET_CMD" $opt 2>&1 | head -50
    echo "rc=${PIPESTATUS[0]}"
  done
} > "$OUT/environment.txt" 2>&1

for src in "$HERE"/cases/$PATTERN.m5 "$HERE"/cases/$PATTERN.m6; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  case_dir="$OUT/${name%.*}"
  mkdir -p "$case_dir"
  cp "$src" "$case_dir/"
  if [ -n "${MORET_LIBR:-}" ]; then
    sed -i "s/jeff311\.xml/$MORET_LIBR/g" "$case_dir/$name"
  fi
  echo ">>> $name"
  (
    cd "$case_dir" || exit 99
    ls -A > .files_before
    start=$(date +%s)
    "$MORET_CMD" $OPTS $RELEASE "$name" > stdout.txt 2> stderr.txt
    rc=$?
    # Erreur d'appel du lanceur (argparse, rc=2) : inutile de poursuivre
    if [ "$rc" -eq 2 ] && grep -q "^usage:" stderr.txt; then
      echo "Appel du lanceur refuse (usage) :" >&2
      cat stderr.txt >&2
      exit 98
    fi
    # Echec d'environnement masque par un code retour 0 (ex. singularity introuvable)
    if grep -qiE "command not found|commande introuvable" stderr.txt; then
      echo "Echec d'environnement du lanceur (rc=$rc) :" >&2
      cat stderr.txt >&2
      exit 98
    fi
    end=$(date +%s)
    echo "$rc" > .exit_code
    echo "$((end - start))" > .duration_s
    # Liste recursive de tout ce qui a ete produit (H1 : nommage/emplacement)
    find . -mindepth 1 -printf '%y %10s %p\n' | sort -k3 > .files_after
    # Fichiers trop gros : remplaces par un extrait (debut/fin) pour l archive
    find . -type f -size +"${MAX_SIZE}"c | while read -r big; do
      { head -c 200000 "$big"; echo; echo "[... tronque ...]"; tail -c 200000 "$big"; } > "$big.truncated"
      rm -f "$big"
    done
    echo "    rc=$rc  duree=$((end - start))s"
  )
  if [ $? -eq 98 ]; then
    echo "Arret : verifier MORET_CMD / MORET_RELEASE / environnement (resultats partiels dans $OUT)" >&2
    exit 2
  fi
done

python3 "$HERE/summarize.py" "$OUT" | tee "$OUT/summary.txt"

tar -czf "$OUT.tar.gz" -C "$HERE" "$(basename "$OUT")"
echo
echo "Archive a transmettre : $OUT.tar.gz"
