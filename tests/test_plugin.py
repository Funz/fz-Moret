#!/usr/bin/env python3
"""
Test suite for the Moret plugin

This script validates the plugin structure and functionality.
"""

import json
import os
import sys

def test_model_files():
    """Test model JSON file exists and is valid"""
    print("\n=== Testing Model Files ===")

    # Check file exists
    model_path = '.fz/models/Moret.json'
    assert os.path.exists(model_path), f"Model file not found: {model_path}"
    print(f"✓ Model file exists: {model_path}")

    # Check valid JSON
    with open(model_path, 'r') as f:
        model = json.load(f)
    print(f"✓ Valid JSON")

    # Check required fields
    required_fields = ['id', 'varprefix', 'delim', 'commentline', 'output']
    expected_outputs = ['moret_status', 'mean_keff', 'sigma_keff', 'dkeff', 'sigma_dkeff']
    for field in required_fields:
        assert field in model, f"Missing required field: {field}"
        print(f"✓ Has field '{field}': {model[field] if field != 'output' else f'{len(model[field])} outputs'}")

    # Check output variables
    assert len(model['output']) > 0, "No output variables defined"
    for name in expected_outputs:
        assert name in model['output'], f"Missing output variable: {name}"
    print(f"✓ Output variables: {', '.join(model['output'].keys())}")

    print("✓ Model files test PASSED")

def test_calculator_files():
    """Test calculator JSON file exists and is valid"""
    print("\n=== Testing Calculator Files ===")

    # Check file exists
    calc_path = '.fz/calculators/localhost_Moret.json'
    assert os.path.exists(calc_path), f"Calculator file not found: {calc_path}"
    print(f"✓ Calculator file exists: {calc_path}")

    # Check valid JSON
    with open(calc_path, 'r') as f:
        calc = json.load(f)
    print(f"✓ Valid JSON")

    # Check required fields
    assert 'uri' in calc, "Missing 'uri' field"
    assert 'models' in calc, "Missing 'models' field"
    print(f"✓ Has field 'uri': {calc['uri']}")
    print(f"✓ Has field 'models': {list(calc['models'].keys())}")

    print("✓ Calculator files test PASSED")

def test_calculator_scripts():
    """Test calculator script exists and is executable"""
    print("\n=== Testing Calculator Scripts ===")

    # Check file exists
    script_path = '.fz/calculators/Moret.sh'
    assert os.path.exists(script_path), f"Calculator script not found: {script_path}"
    print(f"✓ Calculator script exists: {script_path}")

    # Check executable
    assert os.access(script_path, os.X_OK), f"Script not executable: {script_path}"
    print(f"✓ Script is executable")

    # Check shebang
    with open(script_path, 'r') as f:
        first_line = f.readline().strip()
    assert first_line.startswith('#!/'), "Script missing shebang"
    print(f"✓ Has shebang: {first_line}")

    print("✓ Calculator scripts test PASSED")

def test_example_files():
    """Test example files exist"""
    print("\n=== Testing Example Files ===")

    # Check example file exists (MORET 6 example; godiva.m5 kept for MORET 5)
    assert os.path.exists('examples/Moret/godiva.m5'), "MORET 5 example missing"
    example_path = 'examples/Moret/godiva.m6'
    assert os.path.exists(example_path), f"Example file not found: {example_path}"
    print(f"✓ Example file exists: {example_path}")

    # Check file has content
    with open(example_path, 'r') as f:
        content = f.read()
    assert len(content) > 0, "Example file is empty"
    assert 'MORET_BEGIN' in content, "Example file missing MORET_BEGIN marker"
    print(f"✓ Example file has valid MORET format")

    # Check for variables with new delimiter
    assert '${' in content, "Example file should contain variables with ${} syntax"
    print(f"✓ Example file contains parametrized variables")

    print("✓ Example files test PASSED")

def test_with_fz():
    """Test integration with fz framework (if installed)"""
    print("\n=== Testing fz Integration ===")

    try:
        import fz
        print(f"✓ fz module imported successfully")

        # Test variable parsing
        example_path = 'examples/Moret/godiva.m6'
        variables = fz.fzi(example_path, 'Moret')
        print(f"✓ fz.fzi() works, found variables: {list(variables.keys())}")

        # Check expected variables
        expected_vars = ['radius', 'u5']
        for var in expected_vars:
            assert var in variables, f"Expected variable '{var}' not found"
        print(f"✓ Found expected variables: {expected_vars}")

        # Test compilation
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            fz.fzc(
                example_path,
                {'radius': 8.5, 'u5': 4.5e-02},
                'Moret',
                output_dir=tmpdir
            )
            # fz.fzc creates a subdirectory with parameter values in the name
            subdirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            assert len(subdirs) > 0, "No compiled directory created"

            compiled_file = os.path.join(tmpdir, subdirs[0], 'godiva.m6')
            assert os.path.exists(compiled_file), f"Compiled file not found at {compiled_file}"

            # Check variable substitution
            with open(compiled_file, 'r') as f:
                content = f.read()
            assert '8.5' in content, "radius value not substituted"
            assert '4.5' in content or '0.045' in content, "u5 value not substituted"
            print(f"✓ fz.fzc() works, variables substituted correctly")

        print("✓ fz integration test PASSED")

    except ImportError:
        print("⚠ fz module not installed, skipping integration tests")
        print("  Install with: pip install git+https://github.com/Funz/fz.git")
        print("  Then install plugin: python -c 'import fz; fz.install(\"Moret\")'")
    except Exception as e:
        print(f"✗ fz integration test FAILED: {e}")
        raise

def main():
    """Run all tests"""
    print("=" * 60)
    print("Moret Plugin Test Suite")
    print("=" * 60)

    # Change to repository root if needed
    if os.path.exists('tests') and os.path.basename(os.getcwd()) == 'tests':
        os.chdir('..')
        print(f"Changed directory to: {os.getcwd()}")

    failed = False

    # Run all tests
    tests = [
        test_model_files,
        test_calculator_files,
        test_calculator_scripts,
        test_example_files,
        test_with_fz
    ]

    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ Test FAILED: {e}")
            failed = True
        except Exception as e:
            print(f"✗ Test ERROR: {e}")
            failed = True

    print("\n" + "=" * 60)
    if failed:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1
    else:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0

if __name__ == '__main__':
    sys.exit(main())
