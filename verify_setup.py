#!/usr/bin/env python3
"""
ICT AutoTrader Environment Setup Verification Script

This script validates that the complete project setup is correctly configured:
- Python package imports from all src modules
- Configuration file structure and loading
- Environment variables and .env file
- Dependency availability
- Directory permissions

Run this before starting development to ensure environment is ready.

Usage:
    python verify_setup.py
    python verify_setup.py --verbose
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
import importlib
import argparse


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class EnvironmentValidator:
    """Validates the ICT AutoTrader development environment"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[Tuple[str, bool, str]] = []
        self.project_root = Path(__file__).parent.resolve()

    def log(self, message: str, level: str = "info"):
        """Print messages based on verbosity"""
        if self.verbose or level == "error":
            prefix = {
                "info": f"{Colors.BLUE}ℹ{Colors.RESET}",
                "success": f"{Colors.GREEN}✓{Colors.RESET}",
                "error": f"{Colors.RED}✗{Colors.RESET}",
                "warning": f"{Colors.YELLOW}⚠{Colors.RESET}"
            }.get(level, "")
            print(f"{prefix} {message}")

    def add_result(self, test_name: str, passed: bool, details: str = ""):
        """Record a test result"""
        self.results.append((test_name, passed, details))
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"[{status}] {test_name}")
        if details and (not passed or self.verbose):
            print(f"      {details}")

    def validate_imports(self) -> bool:
        """Test all package imports from src modules"""
        self.log("Validating Python package imports...", "info")

        modules_to_test = [
            'src.core',
            'src.data',
            'src.strategy',
            'src.execution',
            'src.notification'
        ]

        all_passed = True
        for module_name in modules_to_test:
            try:
                importlib.import_module(module_name)
                self.add_result(f"Import {module_name}", True, f"Module imported successfully")
            except ImportError as e:
                self.add_result(f"Import {module_name}", False, f"ImportError: {str(e)}")
                all_passed = False
            except Exception as e:
                self.add_result(f"Import {module_name}", False, f"Unexpected error: {str(e)}")
                all_passed = False

        return all_passed

    def validate_config_yaml(self) -> bool:
        """Validate config.yaml structure and loading"""
        self.log("Validating config.yaml...", "info")

        config_path = self.project_root / "config.yaml"

        # Check file exists
        if not config_path.exists():
            self.add_result("config.yaml exists", False, f"File not found at {config_path}")
            return False

        self.add_result("config.yaml exists", True, f"Found at {config_path}")

        # Test PyYAML loading
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.add_result("config.yaml loads with PyYAML", True, "YAML parsing successful")

            # Validate required fields
            required_fields = ['use_testnet', 'symbol', 'interval', 'risk_per_trade']
            missing_fields = [field for field in required_fields if field not in config]

            if missing_fields:
                self.add_result("config.yaml structure", False,
                              f"Missing required fields: {', '.join(missing_fields)}")
                return False

            self.add_result("config.yaml structure", True,
                          f"All required fields present: {', '.join(required_fields)}")

            # Validate use_testnet is boolean
            if not isinstance(config.get('use_testnet'), bool):
                self.add_result("config.yaml use_testnet type", False,
                              f"use_testnet should be boolean, got {type(config['use_testnet'])}")
                return False

            self.add_result("config.yaml use_testnet type", True,
                          f"use_testnet is correctly set to {config['use_testnet']}")

            return True

        except yaml.YAMLError as e:
            self.add_result("config.yaml loads with PyYAML", False, f"YAML parsing error: {str(e)}")
            return False
        except Exception as e:
            self.add_result("config.yaml loads with PyYAML", False, f"Unexpected error: {str(e)}")
            return False

    def validate_env_file(self) -> bool:
        """Validate .env file and python-dotenv loading"""
        self.log("Validating .env file...", "info")

        env_path = self.project_root / ".env"
        env_example_path = self.project_root / ".env.example"

        # Check .env.example exists
        if not env_example_path.exists():
            self.add_result(".env.example exists", False, "Template file not found")
            return False

        self.add_result(".env.example exists", True, "Template file found")

        # Check .env exists (warning if not)
        if not env_path.exists():
            self.add_result(".env exists", False,
                          "Create .env file from .env.example template")
            self.log("⚠ Copy .env.example to .env and configure your API keys", "warning")
            # This is not a fatal error, just a warning
        else:
            self.add_result(".env exists", True, "Environment file found")

        # Test python-dotenv loading
        try:
            from dotenv import load_dotenv

            # Test loading (even if file doesn't exist, function should work)
            load_dotenv(env_path, override=False)
            self.add_result("python-dotenv loads", True, "dotenv module functional")

            # If .env exists, check for required variables
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_content = f.read()

                required_vars = [
                    'BINANCE_TESTNET_API_KEY',
                    'BINANCE_TESTNET_API_SECRET',
                    'DISCORD_WEBHOOK_URL'
                ]

                missing_vars = []
                placeholder_vars = []

                for var in required_vars:
                    if var not in env_content:
                        missing_vars.append(var)
                    elif f'{var}=your_' in env_content or f'{var}=' in env_content.replace(f'{var}=\n', f'{var}='):
                        placeholder_vars.append(var)

                if missing_vars:
                    self.add_result(".env required variables", False,
                                  f"Missing: {', '.join(missing_vars)}")
                elif placeholder_vars:
                    self.add_result(".env configured", False,
                                  f"Still using placeholders: {', '.join(placeholder_vars)}")
                else:
                    self.add_result(".env configured", True, "All required variables present")

            return True

        except ImportError as e:
            self.add_result("python-dotenv loads", False, f"ImportError: {str(e)}")
            return False
        except Exception as e:
            self.add_result("python-dotenv loads", False, f"Unexpected error: {str(e)}")
            return False

    def validate_dependencies(self) -> bool:
        """Validate all dependencies from requirements.txt are installed"""
        self.log("Validating installed dependencies...", "info")

        requirements_path = self.project_root / "requirements.txt"

        if not requirements_path.exists():
            self.add_result("requirements.txt exists", False, "File not found")
            return False

        self.add_result("requirements.txt exists", True, "Requirements file found")

        # Parse requirements.txt
        try:
            with open(requirements_path, 'r') as f:
                lines = f.readlines()

            # Extract package names (ignore comments and version specifiers)
            packages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before >= or ==)
                    pkg_name = line.split('>=')[0].split('==')[0].strip()
                    if pkg_name:
                        packages.append(pkg_name)

            self.log(f"Found {len(packages)} packages in requirements.txt", "info")

            # Test each package import
            all_installed = True
            for pkg_name in packages:
                # Handle package name to module name mapping
                module_name = pkg_name.replace('-', '_')

                try:
                    importlib.import_module(module_name)
                    self.add_result(f"Dependency: {pkg_name}", True, "Installed and importable")
                except ImportError:
                    self.add_result(f"Dependency: {pkg_name}", False,
                                  "Not installed or not importable")
                    all_installed = False
                except Exception as e:
                    self.add_result(f"Dependency: {pkg_name}", False,
                                  f"Error checking: {str(e)}")
                    all_installed = False

            return all_installed

        except Exception as e:
            self.add_result("Parse requirements.txt", False, f"Error: {str(e)}")
            return False

    def validate_logs_directory(self) -> bool:
        """Validate logs directory exists and is writable"""
        self.log("Validating logs directory...", "info")

        logs_dir = self.project_root / "logs"

        # Check directory exists
        if not logs_dir.exists():
            self.add_result("logs/ directory exists", False, "Directory not found")
            return False

        self.add_result("logs/ directory exists", True, "Directory found")

        # Check directory is writable
        test_file = logs_dir / ".write_test"
        try:
            with open(test_file, 'w') as f:
                f.write("write test")

            self.add_result("logs/ directory writable", True, "Write permission confirmed")

            # Clean up test file
            if test_file.exists():
                test_file.unlink()

            return True

        except PermissionError:
            self.add_result("logs/ directory writable", False, "Permission denied")
            return False
        except Exception as e:
            self.add_result("logs/ directory writable", False, f"Error: {str(e)}")
            return False

    def validate_gitignore(self) -> bool:
        """Validate .gitignore excludes sensitive files"""
        self.log("Validating .gitignore configuration...", "info")

        gitignore_path = self.project_root / ".gitignore"

        if not gitignore_path.exists():
            self.add_result(".gitignore exists", False, "File not found")
            return False

        self.add_result(".gitignore exists", True, "File found")

        try:
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()

            # Check for critical exclusions
            critical_patterns = {
                '.env': '.env file (contains API keys)',
                'logs/': 'logs directory'
            }

            all_present = True
            for pattern, description in critical_patterns.items():
                if pattern in gitignore_content:
                    self.add_result(f".gitignore excludes {pattern}", True,
                                  f"Protected: {description}")
                else:
                    self.add_result(f".gitignore excludes {pattern}", False,
                                  f"Should exclude {description}")
                    all_present = False

            return all_present

        except Exception as e:
            self.add_result(".gitignore validation", False, f"Error: {str(e)}")
            return False

    def print_summary(self):
        """Print summary of all validation results"""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}VALIDATION SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

        total_tests = len(self.results)
        passed_tests = sum(1 for _, passed, _ in self.results if passed)
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed_tests}{Colors.RESET}")

        if failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED{Colors.RESET}")
            print(f"{Colors.GREEN}Environment is ready for development!{Colors.RESET}\n")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME CHECKS FAILED{Colors.RESET}")
            print(f"{Colors.RED}Please fix the issues above before proceeding.{Colors.RESET}\n")

            # List failed tests
            print(f"{Colors.BOLD}Failed Tests:{Colors.RESET}")
            for test_name, passed, details in self.results:
                if not passed:
                    print(f"  • {test_name}")
                    if details:
                        print(f"    {details}")
            print()

            return False

    def run_all_validations(self) -> bool:
        """Run all validation tests"""
        print(f"\n{Colors.BOLD}ICT AutoTrader Environment Validation{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

        # Run all validation tests
        self.validate_imports()
        print()

        self.validate_config_yaml()
        print()

        self.validate_env_file()
        print()

        self.validate_dependencies()
        print()

        self.validate_logs_directory()
        print()

        self.validate_gitignore()
        print()

        # Print summary
        return self.print_summary()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate ICT AutoTrader environment setup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_setup.py          # Run validation with standard output
  python verify_setup.py -v       # Run with verbose output
  python verify_setup.py --verbose # Run with verbose output
        """
    )
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    validator = EnvironmentValidator(verbose=args.verbose)

    try:
        success = validator.run_all_validations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validation interrupted by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error during validation: {str(e)}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
