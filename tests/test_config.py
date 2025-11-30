"""
Test suite for configuration file validation.
Tests .env and config.yaml parsing and required keys.
"""

import os
import yaml
import pytest
from pathlib import Path
from dotenv import load_dotenv


class TestConfigurationFiles:
    """Test configuration file structure and parsing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent
        self.env_example_path = self.project_root / ".env.example"
        self.config_yaml_path = self.project_root / "config.yaml"

    def test_env_example_exists(self):
        """Test that .env.example file exists."""
        assert self.env_example_path.exists(), ".env.example file not found"

    def test_env_example_has_required_keys(self):
        """Test that .env.example contains all required environment variables."""
        with open(self.env_example_path, 'r') as f:
            content = f.read()

        # Testnet API keys (required)
        testnet_keys = [
            'BINANCE_TESTNET_API_KEY',
            'BINANCE_TESTNET_API_SECRET',
        ]

        # Mainnet API keys (required for production support)
        mainnet_keys = [
            'BINANCE_MAINNET_API_KEY',
            'BINANCE_MAINNET_API_SECRET',
        ]

        # Discord notification
        notification_keys = [
            'DISCORD_WEBHOOK_URL'
        ]

        all_required_keys = testnet_keys + mainnet_keys + notification_keys

        for key in all_required_keys:
            assert key in content, f"Required key '{key}' not found in .env.example"

    def test_env_example_loads_without_error(self):
        """Test that .env.example can be loaded by python-dotenv."""
        # Create a temporary .env file for testing
        temp_env = self.project_root / ".env.test"
        try:
            # Copy .env.example to .env.test
            with open(self.env_example_path, 'r') as src:
                with open(temp_env, 'w') as dst:
                    dst.write(src.read())

            # Load the temporary .env file
            load_dotenv(temp_env)

            # Verify we can read the testnet variables (even if they're placeholder values)
            assert os.getenv('BINANCE_TESTNET_API_KEY') is not None
            assert os.getenv('BINANCE_TESTNET_API_SECRET') is not None

            # Verify we can read the mainnet variables
            assert os.getenv('BINANCE_MAINNET_API_KEY') is not None
            assert os.getenv('BINANCE_MAINNET_API_SECRET') is not None

            # Verify Discord webhook
            assert os.getenv('DISCORD_WEBHOOK_URL') is not None

        finally:
            # Clean up temporary file
            if temp_env.exists():
                temp_env.unlink()

    def test_config_yaml_exists(self):
        """Test that config.yaml file exists."""
        assert self.config_yaml_path.exists(), "config.yaml file not found"

    def test_config_yaml_parses_correctly(self):
        """Test that config.yaml can be parsed by PyYAML."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        assert config is not None, "config.yaml failed to parse"
        assert isinstance(config, dict), "config.yaml should parse to a dictionary"

    def test_config_yaml_has_required_keys(self):
        """Test that config.yaml contains all required configuration keys."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        # Required top-level keys
        required_keys = [
            'symbol',
            'interval',
            'use_testnet',
            'risk_per_trade',
            'max_daily_loss_percent',
            'max_position_percent',
            'max_trades_per_day',
            'min_body_ratio',
            'fvg_min_gap_percent'
        ]

        for key in required_keys:
            assert key in config, f"Required key '{key}' not found in config.yaml"

    def test_config_yaml_symbol_format(self):
        """Test that symbol is in correct format."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        symbol = config.get('symbol')
        assert isinstance(symbol, str), "symbol should be a string"
        assert symbol == 'BTCUSDT', "symbol should be BTCUSDT for initial setup"

    def test_config_yaml_interval_format(self):
        """Test that interval is in correct format."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        interval = config.get('interval')
        assert isinstance(interval, str), "interval should be a string"
        assert interval == '15m', "interval should be 15m for initial setup"

    def test_config_yaml_use_testnet_is_true(self):
        """Test that use_testnet is set to true for safety."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        use_testnet = config.get('use_testnet')
        assert isinstance(use_testnet, bool), "use_testnet should be a boolean"
        assert use_testnet is True, "use_testnet should be True for initial setup"

    def test_config_yaml_risk_parameters_are_numeric(self):
        """Test that all risk parameters are numeric values."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        numeric_params = [
            'risk_per_trade',
            'max_daily_loss_percent',
            'max_position_percent',
            'min_body_ratio',
            'fvg_min_gap_percent'
        ]

        for param in numeric_params:
            value = config.get(param)
            assert isinstance(value, (int, float)), f"{param} should be numeric"
            assert value > 0, f"{param} should be positive"

    def test_config_yaml_max_trades_is_integer(self):
        """Test that max_trades_per_day is an integer."""
        with open(self.config_yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        max_trades = config.get('max_trades_per_day')
        assert isinstance(max_trades, int), "max_trades_per_day should be an integer"
        assert max_trades > 0, "max_trades_per_day should be positive"
