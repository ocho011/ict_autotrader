# Environment Verification Guide

## Overview

The `verify_setup.py` script validates your ICT AutoTrader development environment to ensure all components are correctly configured before you start development.

## Quick Start

```bash
# Run basic validation
python3 verify_setup.py

# Run with verbose output for detailed information
python3 verify_setup.py --verbose
python3 verify_setup.py -v
```

## What Gets Validated

### 1. Module Imports ✓
- Tests all Python package imports from `src/` modules
- Validates: `src.core`, `src.data`, `src.strategy`, `src.execution`, `src.notification`
- Ensures your Python environment can access all project modules

### 2. Configuration Files ✓
- **config.yaml**:
  - Validates file exists and loads correctly with PyYAML
  - Checks required fields: `use_testnet`, `symbol`, `interval`, `risk_per_trade`
  - Validates `use_testnet` is boolean type

- **.env file**:
  - Checks `.env.example` template exists
  - Warns if `.env` file is missing (you need to create it)
  - Validates environment variables can be loaded with python-dotenv
  - Checks for placeholder values that need to be configured

### 3. Dependencies ✓
- Parses `requirements.txt`
- Verifies each package is installed and importable
- Tests: python-binance, python-dotenv, pyyaml, aiohttp, loguru, pydantic

### 4. Directory Permissions ✓
- Validates `logs/` directory exists
- Tests write permissions by creating a temporary file
- Ensures application can write log files

### 5. Git Configuration ✓
- Checks `.gitignore` exists
- Validates sensitive files are excluded:
  - `.env` (contains API keys)
  - `logs/` (contains runtime data)

## Exit Codes

The script uses standard exit codes for CI/CD integration:

- `0`: All validations passed ✓
- `1`: Some validations failed ✗
- `130`: User interrupted (Ctrl+C)

## Example Output

### Successful Validation
```
ICT AutoTrader Environment Validation
======================================================================

[PASS] Import src.core
[PASS] Import src.data
[PASS] Import src.strategy
[PASS] Import src.execution
[PASS] Import src.notification

[PASS] config.yaml exists
[PASS] config.yaml loads with PyYAML
[PASS] config.yaml structure
[PASS] config.yaml use_testnet type

...

======================================================================
VALIDATION SUMMARY
======================================================================

Total Tests: 24
Passed: 24
Failed: 0

✓ ALL CHECKS PASSED
Environment is ready for development!
```

### Failed Validation Example
```
[FAIL] .env exists
       Create .env file from .env.example template
[FAIL] Dependency: python-binance
       Not installed or not importable

======================================================================
VALIDATION SUMMARY
======================================================================

Total Tests: 24
Passed: 20
Failed: 4

✗ SOME CHECKS FAILED
Please fix the issues above before proceeding.

Failed Tests:
  • .env exists
    Create .env file from .env.example template
  • Dependency: python-binance
    Not installed or not importable
```

## Fixing Common Issues

### Missing .env File
```bash
# Copy the example template
cp .env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor

# Required variables:
# - BINANCE_TESTNET_API_KEY
# - BINANCE_TESTNET_API_SECRET
# - DISCORD_WEBHOOK_URL
```

### Missing Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# Or install specific missing package
pip install python-binance
```

### Logs Directory Issues
```bash
# Create logs directory if missing
mkdir -p logs

# Fix permissions if needed
chmod 755 logs
```

## Integration with CI/CD

The script can be used in CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Validate Environment
  run: python3 verify_setup.py

# The step will fail if validation doesn't pass (exit code 1)
```

## Running Tests

The verification script has a comprehensive test suite:

```bash
# Run all tests
pytest tests/test_verify_setup.py -v

# Run with coverage
pytest tests/test_verify_setup.py --cov=verify_setup --cov-report=html

# Run specific test
pytest tests/test_verify_setup.py::TestEnvironmentValidator::test_validate_imports_success
```

## Features

### Colored Output
- **GREEN**: Tests that passed
- **RED**: Tests that failed
- **YELLOW**: Warnings
- **BLUE**: Informational messages

### Verbose Mode
Use `--verbose` or `-v` flag for detailed information:
- Shows all validation steps
- Displays file paths and configuration values
- Helpful for debugging setup issues

### Security Focus
- Validates sensitive files are excluded from git
- Checks for placeholder API keys
- Ensures proper file permissions

## Support

If you encounter issues:
1. Run with verbose mode: `python3 verify_setup.py --verbose`
2. Check the detailed error messages
3. Refer to README.md for setup instructions
4. Review requirements.txt for dependency versions

## Development

The validation script is located at `/verify_setup.py` and consists of:
- **EnvironmentValidator** class: Main validation logic
- **Colors** class: Terminal color codes
- **main()** function: CLI entry point with argparse

Test suite location: `/tests/test_verify_setup.py`
- 25 comprehensive tests
- Covers all validation scenarios
- Uses pytest with fixtures and mocking
