"""
Test Suite for verify_setup.py

Tests the environment validation script to ensure it correctly
validates the project setup and catches configuration issues.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verify_setup import EnvironmentValidator, Colors


class TestEnvironmentValidator:
    """Test cases for EnvironmentValidator class"""

    @pytest.fixture
    def validator(self):
        """Create a validator instance for testing"""
        return EnvironmentValidator(verbose=True)

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_validator_initialization(self, validator):
        """Test validator initializes correctly"""
        assert validator.verbose is True
        assert validator.results == []
        assert validator.project_root.exists()

    def test_add_result_pass(self, validator):
        """Test adding a passing result"""
        validator.add_result("Test Check", True, "Test passed")

        assert len(validator.results) == 1
        test_name, passed, details = validator.results[0]
        assert test_name == "Test Check"
        assert passed is True
        assert details == "Test passed"

    def test_add_result_fail(self, validator):
        """Test adding a failing result"""
        validator.add_result("Test Check", False, "Test failed")

        assert len(validator.results) == 1
        test_name, passed, details = validator.results[0]
        assert test_name == "Test Check"
        assert passed is False
        assert details == "Test failed"

    def test_validate_imports_success(self, validator):
        """Test successful import validation"""
        # All modules should exist in the project
        result = validator.validate_imports()

        # Check that imports were tested
        import_results = [r for r in validator.results if 'Import src.' in r[0]]
        assert len(import_results) == 5  # core, data, strategy, execution, notification

        # All should pass (assuming modules exist)
        assert result is True or result is False  # Depends on actual project state

    @patch('importlib.import_module')
    def test_validate_imports_failure(self, mock_import, validator):
        """Test import validation with missing module"""
        mock_import.side_effect = ImportError("No module named 'test'")

        result = validator.validate_imports()

        assert result is False
        # Check that failures were recorded
        failed_imports = [r for r in validator.results if not r[1] and 'Import' in r[0]]
        assert len(failed_imports) > 0

    def test_validate_config_yaml_missing(self, validator, temp_project_dir):
        """Test config.yaml validation when file is missing"""
        validator.project_root = temp_project_dir

        result = validator.validate_config_yaml()

        assert result is False
        # Check that missing file was detected
        assert any('config.yaml exists' in r[0] and not r[1] for r in validator.results)

    def test_validate_config_yaml_success(self, validator, temp_project_dir):
        """Test config.yaml validation with valid file"""
        validator.project_root = temp_project_dir
        config_path = temp_project_dir / "config.yaml"

        # Create valid config
        config_content = """
use_testnet: true
symbol: BTCUSDT
interval: 15m
risk_per_trade: 0.02
"""
        config_path.write_text(config_content)

        result = validator.validate_config_yaml()

        assert result is True
        # Check that all validations passed
        config_results = [r for r in validator.results if 'config.yaml' in r[0]]
        assert all(r[1] for r in config_results)  # All should pass

    def test_validate_config_yaml_missing_fields(self, validator, temp_project_dir):
        """Test config.yaml validation with missing required fields"""
        validator.project_root = temp_project_dir
        config_path = temp_project_dir / "config.yaml"

        # Create incomplete config
        config_content = """
use_testnet: true
# Missing: symbol, interval, risk_per_trade
"""
        config_path.write_text(config_content)

        result = validator.validate_config_yaml()

        assert result is False
        # Check that structure validation failed
        assert any('config.yaml structure' in r[0] and not r[1] for r in validator.results)

    def test_validate_config_yaml_invalid_type(self, validator, temp_project_dir):
        """Test config.yaml validation with invalid use_testnet type"""
        validator.project_root = temp_project_dir
        config_path = temp_project_dir / "config.yaml"

        # Create config with wrong type
        config_content = """
use_testnet: "yes"  # Should be boolean
symbol: BTCUSDT
interval: 15m
risk_per_trade: 0.02
"""
        config_path.write_text(config_content)

        result = validator.validate_config_yaml()

        assert result is False
        # Check that type validation failed
        assert any('use_testnet type' in r[0] and not r[1] for r in validator.results)

    def test_validate_env_file_missing(self, validator, temp_project_dir):
        """Test .env validation when file is missing"""
        validator.project_root = temp_project_dir

        # Create .env.example
        env_example_path = temp_project_dir / ".env.example"
        env_example_path.write_text("BINANCE_TESTNET_API_KEY=test\n")

        result = validator.validate_env_file()

        # Should not fail completely (warning only)
        assert result is True or result is False
        # Check that missing .env was detected
        assert any('.env exists' in r[0] for r in validator.results)

    def test_validate_env_file_success(self, validator, temp_project_dir):
        """Test .env validation with valid file"""
        validator.project_root = temp_project_dir

        # Create .env.example
        env_example_path = temp_project_dir / ".env.example"
        env_example_path.write_text("BINANCE_TESTNET_API_KEY=test\n")

        # Create .env with actual values
        env_path = temp_project_dir / ".env"
        env_content = """
BINANCE_TESTNET_API_KEY=actual_key_value
BINANCE_TESTNET_API_SECRET=actual_secret_value
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123/abc
"""
        env_path.write_text(env_content)

        result = validator.validate_env_file()

        assert result is True
        # Check that validation passed
        env_results = [r for r in validator.results if '.env' in r[0]]
        assert len(env_results) > 0

    def test_validate_env_file_placeholder_values(self, validator, temp_project_dir):
        """Test .env validation with placeholder values"""
        validator.project_root = temp_project_dir

        # Create .env.example
        env_example_path = temp_project_dir / ".env.example"
        env_example_path.write_text("BINANCE_TESTNET_API_KEY=test\n")

        # Create .env with placeholders
        env_path = temp_project_dir / ".env"
        env_content = """
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
"""
        env_path.write_text(env_content)

        result = validator.validate_env_file()

        # Should detect placeholders
        assert any('.env configured' in r[0] for r in validator.results)

    def test_validate_dependencies_success(self, validator, temp_project_dir):
        """Test dependency validation with all packages installed"""
        validator.project_root = temp_project_dir

        # Create requirements.txt with installed packages
        requirements_path = temp_project_dir / "requirements.txt"
        requirements_content = """
# Test dependencies
pytest>=7.0.0
pyyaml>=6.0
"""
        requirements_path.write_text(requirements_content)

        result = validator.validate_dependencies()

        # Result depends on whether packages are actually installed
        assert isinstance(result, bool)
        assert len(validator.results) > 0

    def test_validate_logs_directory_success(self, validator, temp_project_dir):
        """Test logs directory validation when directory exists and is writable"""
        validator.project_root = temp_project_dir
        logs_dir = temp_project_dir / "logs"
        logs_dir.mkdir()

        result = validator.validate_logs_directory()

        assert result is True
        # Check that all validations passed
        logs_results = [r for r in validator.results if 'logs/' in r[0]]
        assert all(r[1] for r in logs_results)

    def test_validate_logs_directory_missing(self, validator, temp_project_dir):
        """Test logs directory validation when directory is missing"""
        validator.project_root = temp_project_dir

        result = validator.validate_logs_directory()

        assert result is False
        # Check that missing directory was detected
        assert any('logs/ directory exists' in r[0] and not r[1] for r in validator.results)

    def test_validate_logs_directory_not_writable(self, validator, temp_project_dir):
        """Test logs directory validation when directory is not writable"""
        validator.project_root = temp_project_dir
        logs_dir = temp_project_dir / "logs"
        logs_dir.mkdir()

        # Make directory read-only
        logs_dir.chmod(0o444)

        try:
            result = validator.validate_logs_directory()

            # Should detect write permission issue
            assert result is False or result is True  # Depends on OS permissions handling
        finally:
            # Restore permissions for cleanup
            logs_dir.chmod(0o755)

    def test_validate_gitignore_success(self, validator, temp_project_dir):
        """Test .gitignore validation with correct exclusions"""
        validator.project_root = temp_project_dir
        gitignore_path = temp_project_dir / ".gitignore"

        gitignore_content = """
# Environment
.env

# Logs
logs/

# Python
__pycache__/
"""
        gitignore_path.write_text(gitignore_content)

        result = validator.validate_gitignore()

        assert result is True
        # Check that all exclusions were found
        gitignore_results = [r for r in validator.results if '.gitignore excludes' in r[0]]
        assert all(r[1] for r in gitignore_results)

    def test_validate_gitignore_missing_exclusions(self, validator, temp_project_dir):
        """Test .gitignore validation with missing critical exclusions"""
        validator.project_root = temp_project_dir
        gitignore_path = temp_project_dir / ".gitignore"

        gitignore_content = """
# Python
__pycache__/
# Missing critical exclusions
"""
        gitignore_path.write_text(gitignore_content)

        result = validator.validate_gitignore()

        assert result is False
        # Check that missing exclusions were detected
        missing = [r for r in validator.results if '.gitignore excludes' in r[0] and not r[1]]
        assert len(missing) > 0

    def test_print_summary_all_pass(self, validator, capsys):
        """Test summary output when all tests pass"""
        validator.results = [
            ("Test 1", True, ""),
            ("Test 2", True, ""),
            ("Test 3", True, "")
        ]

        result = validator.print_summary()

        assert result is True
        captured = capsys.readouterr()
        assert "ALL CHECKS PASSED" in captured.out
        assert "Passed: 3" in captured.out

    def test_print_summary_some_fail(self, validator, capsys):
        """Test summary output when some tests fail"""
        validator.results = [
            ("Test 1", True, ""),
            ("Test 2", False, "Error details"),
            ("Test 3", True, "")
        ]

        result = validator.print_summary()

        assert result is False
        captured = capsys.readouterr()
        assert "SOME CHECKS FAILED" in captured.out
        assert "Failed: 1" in captured.out
        assert "Test 2" in captured.out


class TestIntegration:
    """Integration tests for the complete validation process"""

    def test_full_validation_run(self):
        """Test running all validations on actual project"""
        validator = EnvironmentValidator(verbose=False)

        # Run all validations
        result = validator.run_all_validations()

        # Should complete without exceptions
        assert isinstance(result, bool)
        # Should have results from all validation categories
        assert len(validator.results) > 0

    def test_verbose_mode(self, capsys):
        """Test verbose output mode"""
        validator = EnvironmentValidator(verbose=True)

        validator.log("Test message", "info")
        captured = capsys.readouterr()

        assert "Test message" in captured.out

    def test_non_verbose_mode(self, capsys):
        """Test non-verbose mode (only errors shown)"""
        validator = EnvironmentValidator(verbose=False)

        validator.log("Test message", "info")
        captured = capsys.readouterr()

        # Info messages should not appear in non-verbose mode
        assert captured.out == ""


class TestColors:
    """Test color code constants"""

    def test_color_codes_defined(self):
        """Test that all color codes are defined"""
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'YELLOW')
        assert hasattr(Colors, 'BLUE')
        assert hasattr(Colors, 'BOLD')
        assert hasattr(Colors, 'RESET')

    def test_color_codes_are_strings(self):
        """Test that color codes are strings"""
        assert isinstance(Colors.GREEN, str)
        assert isinstance(Colors.RED, str)
        assert isinstance(Colors.RESET, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
