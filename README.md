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

- **File type supported**: `*.m6` (MORET 6), `*.m5` (MORET 5, unverified), any other format for resources
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

This will identify input variables:
- `radius`, expected to vary inside [8.0,9.0]
- `u5`, expected to vary inside [0,1] (by default), with default value 4.49988E-02

### Output

- **Files read**: `<input>.listing` and `<input>.out.xml` (e.g. `godiva.m6.listing`), as named by MORET 6.0.0
- **Extracted values**:

| Variable | Content |
|---|---|
| `moret_status` | `NORMAL END`, `ABNORMAL END: <MORET error message>`, `NO OUTPUT` (no listing) or `NO END BANNER` |
| `mean_keff`, `sigma_keff` | keff and standard deviation of the lowest-sigma estimator (initial system) |
| `dkeff`, `sigma_dkeff` | keff variation of each perturbed system, flattened by fz into `dkeff_1`, `dkeff_2`, ... (absent without perturbation) |

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

1. Install the Funz framework:
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
| `MORET_RELEASE` | `6.0` for `.m6`, `5D1` for `.m5` | first launcher argument (`moret.py {5A1,5B1,5B2,5C1,5D1,6.0} input_file`); set to an empty string for a launcher without it |
| `MORET_OPTS` | none | extra launcher options (e.g. `--keep_tmp_dir`) |

MORET 6 launchers may run MORET in a Singularity container: `singularity` must then be in `PATH`.

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
│       └── godiva.m5               # Legacy MORET 5 example (unverified)
├── tests/
│   ├── test_plugin.py              # Plugin structure and fz integration
│   ├── test_calculator.py          # Moret.sh with a fake launcher
│   ├── test_outputs_moret6.py      # Output extraction on real MORET 6 outputs
│   ├── fixtures/moret6/            # Reference MORET 6.0.0 outputs (anonymized)
│   └── moret_probe/                # Probe datasets to run with a real MORET
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

**Extracted Output Variables:** `moret_status`, `mean_keff`, `sigma_keff`, `dkeff`, `sigma_dkeff` (see [Output](#output)).

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
pytest tests/test_calculator.py tests/test_outputs_moret6.py
```

`tests/moret_probe/` contains short datasets and scripts to check the plugin assumptions against a real MORET installation (see its README).

## Customization

To adapt this plugin for your specific needs:

1. **Modify input syntax**: Edit `.fz/models/Moret.json` to change variable/formula prefixes or delimiters
2. **Add output variables**: Add new extraction commands in the `output` section
3. **Change MORET launcher**: set `MORET_CMD`, `MORET_RELEASE`, `MORET_OPTS` (no script edit needed)
4. **Custom calculator**: Create additional calculator configurations for different execution environments

## Troubleshooting

The calculator decides success from the MORET outputs, not from the launcher exit code
(observed to be 0 even on abnormal end with MORET 6.0.0). Exit codes of `Moret.sh`, reported by fz in the
`error` column together with the MORET message:

| Code | Meaning | Check |
|---|---|---|
| 1 | no `.m6`/`.m5` dataset in the input | input files |
| 4 | launcher not found | `MORET_CMD` |
| 5 | no listing produced | `MORET_RELEASE`, launcher environment (e.g. `singularity` in `PATH`) |
| 6 | MORET abnormal end | dataset (error message in `error` and `moret_status`) |
| 7 | listing without end banner | interrupted run (time limit, crash) |

A failed case is retried by fz up to `FZ_MAX_RETRIES` times (default 5), including deterministic dataset
errors (code 6): set `FZ_MAX_RETRIES=1` while debugging a dataset.

Default random seeds are 0: repeating a case gives identical results. Use `SOUR SEED` for independent replicates.

## Related Resources

- [Funz framework](https://github.com/Funz/fz) - Main parametric computing framework
- [Funz plugins](https://github.com/Funz) - Other available model plugins
- MORET documentation - Consult your MORET installation for detailed usage

## License

This project is licensed under the BSD 3-Clause License - see the LICENSE file for details.
