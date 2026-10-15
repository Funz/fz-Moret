# fz-Moret

Funz plugin for MORET (Monte Carlo neutron transport code for criticality safety)

## Features

This plugin integrates MORET calculations with the Funz parametric computing framework, enabling:
- Automated parametric studies for criticality safety calculations
- Variable substitution in MORET input files
- Formula expressions for derived parameters
- Automatic extraction of keff, its uncertainty and the end status of each run
- Extraction of keff variations of perturbed systems (`ASSO` `REPL` / `TAYL`)

### Input

- **File type supported**: `*.m6` (MORET 6), `*.m5` (MORET 5, verified with 5.D.1), `*.moret`, any other format for resources
- **Parameter syntax**:
  - Variable syntax: `${...}`
  - Formula syntax: `@{...}`
  - Comment char: `*`
  
#### Example input file:

```
MORET_BEGIN
GODIVA - bare HEU metal sphere (MORET 6)

GEOM
  MODU 0
    TYPE 1 SPHE ${radius~[8.0,9.0]}
    VOLU 1 0 1 UMET 0. 0. 0.
  ENDM
ENDG

MATE
  CONT
    LIBR jeff311.xml
    TEMP 300
    COMP UMET
      CONC
        U234 4.91895E-04
        U235 ${u5~4.49988E-02}
        U238 2.49865E-03
    ENDC
  ENDM

SOUR
  UNIF 1000
ENDS
...
ENDD
MORET_END
```

Formulas `@{...}` are evaluated by fz; inside a formula, refer to a variable as `$radius` (without braces), e.g.
`* Sphere mass (kg): @{round(18.74*4/3*3.141592653589793*$radius**3/1000, 2)}` in `examples/Moret/godiva.m6`.

This will identify input variables:
- `radius`, expected to vary inside [8.0,9.0]
- `u5`, expected to vary inside [0,1] (by default), with default value 4.49988E-02

### Output

- **Files read**: `<input>.listing` (e.g. `godiva.m6.listing`), `<input>.out.xml` or `<input>.out.xml.gz` (`OUTP XMLZ 1`), and `moret.log` (launcher output written by `Moret.sh`), as named by MORET 6.0.0 and 5.D.1
- **Extracted values**:

| Variable | Content |
|---|---|
| `moret_status` | `NORMAL END`, `NORMAL END (STOP OPTION, NO SIMULATION)`, `ABNORMAL END: <MORET error message>`, `NO END BANNER[: <crash cause>]` (e.g. `forrtl: error (73): floating divide by zero`) or `NO OUTPUT` (no listing) |
| `mean_keff`, `sigma_keff` | keff and standard deviation of the lowest-sigma estimator (initial system) |
| `keff_estimator` | name of that estimator (e.g. `COMBI. GENERAL`) |
| `active_cycles` | number of active cycles of the final estimate (lower than requested with `TERM KEFF SIGM ... SUPE/INFE/DIFF`) |
| `transient_cycles` | greatest number of initial active cycles to suppress for the stationarity of every estimator (MORET criterion, informative only) |
| `dkeff`, `sigma_dkeff` | keff variation of each perturbed system (`REPL`, `VARD`, `TAYL`; MORET 5 `PERT`), flattened by fz into `dkeff_1`, `dkeff_2`, ... (absent without perturbation) |
| `moret_warnings` | information messages, e.g. `WARN_GEOM 16, WARN_ACE_DATA 2` (`WARN_GEOM 16`: lattice larger than its container, truncated silently) |
| `moret_version` | e.g. `MORET 6.0.0 (commit short hash: 052de83)`: two builds share the same version number |
| `cpu_time` | global CPU time (s) |

#### Example output (listing):

```
##                 CYCLE    100 LOWEST SIGMA ESTI.        0.99381 +/-  0.00203  :  0.98772 < KEFF < 0.99991           ##
...
##                                               PERTURBED SYSTEM NO 1                                                ##
##                 CYCLE    100 LOWEST SIGMA ESTI.    +8.0230E-03 +/- 4.6602E-05 : +7.8831E-03 < DKEFF < +8.1628E-03  ##
```

This returns `mean_keff` = 0.99381, `sigma_keff` = 0.00203, `dkeff_1` = 0.008023, `sigma_dkeff_1` = 4.6602e-05.

## Installation

### Prerequisites

1. Install the Funz framework (fz >= 1.2: the model outputs are `python://` expressions):
   ```bash
   pip install git+https://github.com/Funz/fz.git
   ```

2. Install the Moret plugin:
   ```python
   import fz
   fz.install('Moret')
   ```

3. Make the MORET launcher available and configure it through environment variables:

| Variable | Default | Role |
|---|---|---|
| `MORET_CMD` | `moret.py` on `PATH`, else `/opt/MORET/scripts/moret.py` | launcher |
| `MORET_RELEASE` | `5D1` for `.m5`, `6.0` otherwise | first launcher argument (`moret.py {5A1,5B1,5B2,5C1,5D1,6.0} input_file`); set to an empty string for a launcher taking only the input file (e.g. a MORET 6 container script `moret6.sh`) |
| `MORET_OPTS` | none | extra launcher options (e.g. `--keep_tmp_dir`) |
| `MORET_TMPDIR` | `$TMPDIR`, else `/tmp` | where MORET runs when the case directory contains `,` or `:` (see below) |

MORET 6 launchers may run MORET in a Singularity container: `singularity` must then be in `PATH`.
The container scripts bind the dataset directory with `singularity --bind <dir>:/workdir,...`, which fails
when `<dir>` contains a `,` — and fz names case directories `radius=8.5,u5=0.045`. `Moret.sh` then runs
MORET in a temporary directory under `MORET_TMPDIR` and copies the outputs back.

Launchers verified (see `tests/moret_probe/README.md`): `moret.py 6.0` and a MORET 6 container script
(both MORET 6.0.0, different builds, identical keff), `moret.py 5D1` (MORET 5.D.1). `moret.py` copies back only
`.listing`, `.out.xml` and `.ps`: `.pertu`, `.keff` (`ESTI PRIN`) and `.out.xml.gz` (`XMLZ 1`) stay in its
temporary directory (`--keep_tmp_dir` to keep it).

## Usage

### Quick Start

Open the included Jupyter notebook to see how the plugin works:

```bash
jupyter notebook example_usage.ipynb
```

The notebook demonstrates:
- Parsing input files to identify variables
- Creating parametric templates
- Compiling input files with specific parameter values
- Running parametric studies
- Visualizing results

### Basic Usage

```python
import fz

# Define parameter values
input_variables = {
    "radius": [8.0, 8.5, 9.0],
    "u5": 4.49988E-02
}

# Run parametric study
results = fz.fzr(
    "examples/Moret/godiva.m6",
    input_variables,
    "Moret",
    calculators="localhost_Moret",
    results_dir="moret_results"
)

print(results[["radius", "moret_status", "mean_keff", "sigma_keff"]])
```

### Parsing Input Variables

```python
import fz

# Parse input file to identify variables
variables = fz.fzi("examples/Moret/godiva.m6", "Moret")
print(variables)
```

### Compiling Input Files

```python
import fz

# Compile input file with specific parameter values
fz.fzc(
    "examples/Moret/godiva.m6",
    {"radius": 8.5, "u5": 5.0e-02},
    "Moret",
    output_dir="compiled"
)
```

## Directory Structure

```
fz-Moret/
├── .fz/
│   ├── models/
│   │   └── Moret.json              # Model configuration with syntax rules
│   └── calculators/
│       ├── Moret.sh                # Calculator execution script
│       └── localhost_Moret.json    # Local calculator configuration
├── examples/
│   └── Moret/
│       ├── godiva.m6               # Example MORET 6 input file
│       └── godiva.m5               # Legacy MORET 5 example (MORET 5 syntax, fails under MORET 6)
├── tests/
│   ├── test_plugin.py              # Plugin structure and fz integration
│   ├── test_calculator.py          # Moret.sh with a fake launcher
│   ├── test_outputs.py             # Output extraction on real MORET 6 / 5 outputs
│   ├── test_fz_e2e.py              # fz.fzr end-to-end with a fake launcher
│   ├── fixtures/moret6/, moret5/   # Reference MORET 6.0.0 / 5.D.1 outputs (anonymized)
│   └── moret_probe/                # Probe datasets to run with a real MORET
├── tools/moret_outputs.py          # Output extraction (Python, regular expressions)
├── tools/make_model.py             # Generator of .fz/models/Moret.json (python:// outputs)
├── example_usage.ipynb             # Example usage notebook (Jupyter)
├── .gitignore
├── LICENSE                         # BSD-3-Clause license
└── README.md                       # This file
```

## Configuration

### Model Configuration (`.fz/models/Moret.json`)

Defines the input/output syntax for MORET files:
- `id`: Model identifier (`Moret`)
- `varprefix`: Variable prefix character (`$`)
- `formulaprefix`: Formula prefix character (`@`)
- `delim`: Delimiter around variables (`{}`)
- `commentline`: Comment character (`*`)
- `output`: Shell commands mapping output variable names to extraction methods

**Extracted Output Variables:** see [Output](#output). Each output is a `python://` expression (fz >= 1.2,
no shell needed), generated by `tools/make_model.py` from the plain Python functions of
`tools/moret_outputs.py` (regular expressions on the listing): edit these functions, then run
`python3 tools/make_model.py` (CI runs it with `--check`).

### Calculator Configuration (`.fz/calculators/localhost_Moret.json`)

Specifies execution method and command mappings:
- `uri`: Execution protocol (`sh://` for local shell)
- `models`: Maps model name to execution command

### Remote Execution

To run MORET calculations on a remote server via SSH:

1. Create a new calculator configuration file (e.g., `.fz/calculators/Remote_Moret.json`):
   ```json
   {
       "uri": "ssh://username@hostname",
       "models": {
           "Moret": "MORET_CMD=/path/to/moret.py bash /path/to/Moret.sh"
       }
   }
   ```

2. Use it in your Funz calls:
   ```python
   results = fz.fzr("examples/Moret/godiva.m6", input_variables, "Moret",
                     calculators="Remote_Moret")
   ```

## Testing

Run the test suite to validate the plugin:

```bash
python tests/test_plugin.py
pytest tests/   # test_calculator.py (fake launcher), test_outputs.py (real MORET 6 / 5 outputs), test_fz_e2e.py (fzr)
```

`tests/moret_probe/` contains short datasets and scripts to check the plugin assumptions against a real MORET installation (see its README).

## Customization

To adapt this plugin for your specific needs:

1. **Modify input syntax**: Edit `.fz/models/Moret.json` to change variable/formula prefixes or delimiters
2. **Add output variables**: add a function `name(d)` to `tools/moret_outputs.py` (standard library only), list it in `OUTPUTS`, run `python3 tools/make_model.py`
3. **Change MORET launcher**: set `MORET_CMD`, `MORET_RELEASE`, `MORET_OPTS` (no script edit needed)
4. **Custom calculator**: Create additional calculator configurations for different execution environments

## Troubleshooting

The calculator decides success from the MORET outputs, not from the launcher exit code
(0 with `moret.py` even on abnormal end or crash). Exit codes of `Moret.sh`, reported by fz in the
`error` column together with the MORET message:

| Code | Meaning | Check |
|---|---|---|
| 1 | no `.m6`/`.m5` dataset in the input | input files |
| 4 | launcher not found | `MORET_CMD` |
| 5 | no listing produced | `MORET_RELEASE`, launcher environment (e.g. `singularity` in `PATH`) |
| 6 | MORET abnormal end | dataset (error message in `error` and `moret_status`) |
| 7 | listing without end banner | crash (cause in `moret_status` and `moret.log`) or interrupted run |

A failed case is retried by fz up to `FZ_MAX_RETRIES` times (default 5), including deterministic dataset
errors (code 6): set `FZ_MAX_RETRIES=1` while debugging a dataset.

Default random seeds are 0: repeating a case gives identical results. Use `SOUR SEED` for independent replicates.

### Known limits (verified, not detected by the plugin unless stated)

- A `NORMAL END` with keff and a small sigma does not prove convergence; `transient_cycles` and `moret_warnings` are hints only.
- A lattice larger than its container is truncated without error (wrong keff): check `moret_warnings` for `WARN_GEOM 16`.
- `NOTG` disables the overlap check: overlapping volumes then end normally with a wrong keff.
- A perturbed system identical to the initial one (Δkeff = 0, e.g. a parameter value that cancels the perturbation)
  makes MORET 6.0.0 crash after printing keff and Δkeff: `NO END BANNER: forrtl: error (73): floating divide by zero`.
- `TERM KEFF SIGM s SUPE/INFE/DIFF k` may stop before `s` is reached: check `sigma_keff` and `active_cycles`.
- `VARD` takes no count in MORET 6.0.0 (`VARD 2 0.01 -0.01` means 3 systems, the first one +200 %), unlike the manual; `REPL n a b` and `REPL ( a b )` are equivalent.
- `TAYL ... DENS c`: `c` is relative (0.01 = +1 %); each column is one perturbed system, lines are cumulated.

## Related Resources

- [Funz framework](https://github.com/Funz/fz) - Main parametric computing framework
- [Funz plugins](https://github.com/Funz) - Other available model plugins
- MORET documentation - Consult your MORET installation for detailed usage

## License

This project is licensed under the BSD 3-Clause License - see the LICENSE file for details.
