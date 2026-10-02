# Sondes MORET : consolidation des hypothèses du plugin

Jeux de données courts (Godiva, 1000 neutrons/cycle, 30 cycles inactifs + 100 actifs)
destinés à être lancés avec un MORET réel. Les sorties servent à :

- trancher les hypothèses sur lesquelles reposent `Moret.sh` et l'extraction des sorties de `Moret.json` ;
- confirmer les affirmations des skills MORET (v3 : contradictions entre fichiers alignées sur `input-MORET.md`, sans preuve d'exécution jointe) et trancher les incohérences restantes ;
- fournir des fichiers de référence (`listing`, `out.xml`, ...) pour les tests unitaires du plugin.

## Lancement

```bash
cd tests/moret_probe
MORET_CMD=/chemin/vers/moret.py MORET_RELEASE=6.0 ./run_probe.sh
# MORET_RELEASE : 1er argument du lanceur ({5A1,5B1,5B2,5C1,5D1,6.0}) ; vide si le lanceur n'en prend pas
# MORET_OPTS=--keep_tmp_dir : conserver le répertoire de travail du lanceur (recommandé, H1)
# prérequis MORET 6 : singularity dans le PATH (ex. module load singularity)
# optionnel : MORET_LIBR=endf71.xml (remplace jeff311.xml dans tous les cas)
# optionnel : filtre sur les noms de cas, ex. ./run_probe.sh 'ok_*'
```

MORET 5 : `MORET_RELEASE=5D1 ./run_probe.sh 'm5_*'`. Le script s'arrête au premier refus d'appel
du lanceur (message `usage:`), sans lancer les cas suivants.

Test de bout en bout via fz (depuis la racine du dépôt) :

```bash
MORET_CMD=/chemin/vers/moret.py MORET_RELEASE=6.0 python3 tests/moret_probe/run_fz_e2e.py
```

Exécute le plugin corrigé (`localhost_Moret` → `Moret.sh`, qui lit `MORET_CMD`, `MORET_RELEASE`,
`MORET_OPTS`) sur `examples/Moret/godiva.m6` (rayons 8,5 / 8,7407 / 9,0).

Fichiers à transmettre : `results-<label>-<date>.tar.gz` et `results-fz-e2e/`.
Chaque cas contient l'entrée, `stdout.txt`, `stderr.txt`, le code de retour (`.exit_code`),
la liste des fichiers produits (`.files_after`) et tous les fichiers produits
(tronqués au-delà de 20 Mo). `summary.txt` résume l'ensemble.

## Acquis (1ʳᵉ exécution, 2026-10-01)

- Interface du lanceur : `moret.py [-h] [--keep_tmp_dir] {5A1,5B1,5B2,5C1,5D1,6.0} input_file`
  (« Start APOLLO2 + MORET »). La version est un argument obligatoire ; aucune option `--version`.
- Appel incorrect : erreur argparse, code retour 2, rien n'est produit.
- Conséquence pour le plugin : `Moret.sh` appelle `moret.py <fichier>` sans version, donc échoue
  sur cette installation ; la version (argument) peut servir de `code_id` pour le cache fz (H13).

## Acquis (2ᵉ exécution, 2026-10-01 18:17, MORET 6.0)

- Le lanceur copie l'entrée dans `<entree>_tmp/moret_temp/`, puis exécute MORET 6 dans un conteneur
  Singularity (image du site) ; le
  répertoire temporaire est supprimé en fin d'exécution (option `--keep_tmp_dir` pour le conserver).
- `singularity` absent du PATH de la machine : les 25 cas échouent (`singularity : commande introuvable`)
  **avec un code retour 0** et sans aucun fichier produit. Le code retour du lanceur ne signale donc
  pas les échecs : le plugin doit vérifier la présence et le contenu des sorties.
- `run_probe.sh` vérifie désormais la présence de `singularity` avant de lancer (MORET 6) et
  s'arrête au premier message « command not found / commande introuvable ».

## Acquis (3ᵉ exécution, 2026-10-01 18:29, MORET 6.0.0, 25 cas exécutés)

Fichiers de référence anonymisés : `tests/fixtures/moret6/` ; tests : `tests/test_outputs_moret6.py`.

| Id | Résultat |
|---|---|
| H1 | Sorties `<entrée>.listing`, `<entrée>.out.xml`, `<entrée>.ps` (suffixes ajoutés au nom complet, ex. `godiva.m6.listing`). Pas de `keff`. `.pertu` produit par MORET (liste `output_files`) mais **non recopié** par le lanceur |
| H2 | `##  CYCLE 100 LOWEST SIGMA ESTI.  0.99381 +/-  0.00203 : ...` (anglais) ; Δkeff : `+8.0230E-03 +/- 4.6602E-05` (notation scientifique signée) |
| H3 | `NORMAL END OF THE CALCULATION` / `ABNORMAL END OF THE CALCULATION` ; attention, `NORMAL END` seul correspond aussi à `ABNORMAL END` et à `NORMAL END FOR DATA READING` |
| H4 | `Error message number N from ERROR_xxx ...` + ligne de détail ; **code retour 0 même en fin anormale** |
| H5 | `MORET_BEGIN`/`MORET_END` optionnels : confirmé |
| H6 | `godiva.m5` sous MORET 6 : Error 3 `ERROR_ASSO_MATE_GEOM` (milieu `1`) |
| H7 | Pas d'association par rang : milieu `1` -> Error 3 |
| H8 | `REPL n` et `REPL ( )` équivalents ; U235 +1 % : Δkeff +8,02E-03 (REPL) / +8,09E-03 (TAYL) ; `TAYL DENS 0.01` : +2,6E-04 seulement (suspect, voir H20) |
| H9 | `out.xml` : racine `<calculation>` (structure des skills fausse) ; `keff/esti[@name]/mean` = vecteur indexé par le nombre de cycles initiaux supprimés (1ʳᵉ valeur = aucun) ; `perturbations/dkeff/perturbed_system[@num]/esti` ; `end_message`, `error_message`, `output_files` ; score prédéfini nommé `RATE_KEFF` (skills : `RATES_KEFF`) ; `SUPP KEFF` sans effet visible (recalcul de stationnarité déjà imprimé par défaut) |
| H10 | `MATE` avant `GEOM` accepté ; mots-clés longs acceptés ; **`GRAP` après `MATE` accepté et tracé** (skills : refusé) |
| H13 | Pas d'option de version ; `out.xml` donne `code="MORET 6.0.0"` et `commit_short_hash` |
| H14 | Code retour 0 dans tous les cas (succès comme échec) |
| H16 | Extension `.m5` acceptée par le lanceur 6.0 |
| H17 | `COMP` inutilisée : message informatif « not loaded because they are not used », fin normale ; `COMP` utilisée seulement via `REPL` : fin normale |
| H18 | `SIMU` avant `SOUR` et `TERM` en premier : acceptés |
| H20 | `TAYL ... DENS c` : `c` relatif (skills) ou absolu en g/cm³ ; comparaison à une densité +1 % par `REPL` | `ok_pert_dens_*` |
| H19 | `DLIM` sur `VOLU` : ordre `xmin xmax ymin ymax zmin zmax` confirmé (ordre `ZONI` -> Error 93) ; mais `DLIM` ne borne pas un volume infini pour les sources : Error 4 `ERROR_REPART_SOURCES` (« bounding volume could not be determined ») -> exemple de `error-MORET.md` v3 invalide |
| — | Graine par défaut 0 : résultats identiques d'un calcul à l'autre (réplications : `SOUR SEED`) |
| — | Erreurs confirmées : `!` (Error 14), `SOUR` avant `OUTP` (19), ligne non commentée avant `GEOM` (1), deux volumes externes (6), `XMLC` (20) |

## Hypothèses testées

| Id | Hypothèse | Cas |
|---|---|---|
| H1 | Nom et emplacement des sorties MORET 6 (`listing`, `out.xml`, `keff` ou `<nom>.listing`) | `ok_baseline` |
| H2 | Format de la ligne keff finale (FR `FAIBLE SIGMA` / EN `LOWEST SIGMA`, notation) | `ok_baseline` |
| H3 | Marqueur de fin normale (`NORMAL END OF THE CALCULATION`) | tous les `ok_*` |
| H4 | Format `Error message number N from ERROR_...` et code retour non nul en cas d'erreur | `err_*` |
| H5 | `MORET_BEGIN`/`MORET_END` optionnels | `ok_no_delimiters` |
| H6 | `examples/Moret/godiva.m5` (syntaxe MORET 5) : comportement MORET 5 et MORET 6 | `m5_godiva_example` |
| H7 | Milieu numérique (`VOLU ... 1 ...`) sans `COMP 1` : association par rang ou erreur | `var_medium_numeric`, `err_medium_mismatch` |
| H8 | Format du Δkeff par système perturbé (`REPL n`, `REPL ( )`, `TAYL`) | `ok_pert_*` |
| H9 | Structure de `out.xml` : scores, keff par estimateur, tests de normalité, `SUPP` | `ok_scores`, `ok_supp` |
| H10 | Affirmations des skills v3 : `MATE` avant `GEOM` accepté, mots-clés longs acceptés, `GRAP` immédiatement après `GEOM` | `var_mate_before_geom`, `var_long_keywords`, `var_grap_after_*` |
| H13 | Option de version du lanceur (pour `version_cmd` / cache fz) | `environment.txt` |
| H14 | Code retour 0 en cas de succès | tous les `ok_*` |
| H16 | Le lanceur MORET 6 dépend-il de l'extension `.m5`/`.m6` | `ok_baseline_ext` |
| H17 | `COMP` inutilisée (erreur probable selon v3, non reproduite) ; `COMP` référencée seulement via `ASSO REPL` (légitime selon v3) | `var_comp_unused`, `ok_pert_repl_count` |
| H18 | Position flexible de `SIMU`/`TERM` (v3) | `var_simu_before_sour`, `var_term_first` |
| H20 | `TAYL ... DENS c` : `c` relatif (skills) ou absolu en g/cm³ ; comparaison à une densité +1 % par `REPL` | `ok_pert_dens_*` |
| H19 | `DLIM` sur `VOLU` : ordre `xmin xmax ymin ymax zmin zmax` (différent de `ZONI`) ; borne-t-il le transport d'un volume externe infini (exemple `error-MORET.md` v3) | `var_cyli_dlim_*` |

La première ligne de commentaire de chaque cas (`* Hypothese` / `* Attendu`) rappelle l'objet du test.
Un résultat contraire à « Attendu » est une information, pas un échec : il corrige l'hypothèse.

## Non couvert (jeux de données à fournir)

- Perturbation MORET 5 (`PERTU`) : syntaxe non documentée dans les skills, un jeu de données
  existant est nécessaire pour valider `dkeff_pertu` / `sigma_dkeff_pertu`.
- Listing en anglais et en français : le mécanisme de choix de langue n'est pas connu ;
  si une option existe, relancer `ok_baseline` dans l'autre langue.
