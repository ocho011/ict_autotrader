"""
Test to verify the project directory structure is correctly set up.

This test ensures Task 1.1 (Create Complete Directory Structure) is properly completed.
"""

import os
import importlib
from pathlib import Path


class TestProjectStructure:
    """Verify project directory structure and package initialization."""

    def test_src_directories_exist(self):
        """Verify all source code directories exist."""
        base_path = Path(__file__).parent.parent
        expected_dirs = [
            'src',
            'src/core',
            'src/data',
            'src/strategy',
            'src/execution',
            'src/notification'
        ]

        for dir_path in expected_dirs:
            full_path = base_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} does not exist"
            assert full_path.is_dir(), f"{dir_path} is not a directory"

    def test_test_directories_exist(self):
        """Verify all test directories exist."""
        base_path = Path(__file__).parent.parent
        expected_dirs = [
            'tests',
            'tests/unit',
            'tests/integration',
            'tests/fixtures'
        ]

        for dir_path in expected_dirs:
            full_path = base_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} does not exist"
            assert full_path.is_dir(), f"{dir_path} is not a directory"

    def test_docs_directory_exists(self):
        """Verify docs directory and key files exist."""
        base_path = Path(__file__).parent.parent
        docs_dir = base_path / 'docs'

        assert docs_dir.exists(), "docs/ directory does not exist"
        assert docs_dir.is_dir(), "docs/ is not a directory"

        # Check for key documentation files
        architecture_md = docs_dir / 'architecture.md'
        testing_md = docs_dir / 'testing.md'

        assert architecture_md.exists(), "docs/architecture.md does not exist"
        assert testing_md.exists(), "docs/testing.md does not exist"

    def test_logs_directory_exists(self):
        """Verify logs directory exists."""
        base_path = Path(__file__).parent.parent
        logs_dir = base_path / 'logs'

        assert logs_dir.exists(), "logs/ directory does not exist"
        assert logs_dir.is_dir(), "logs/ is not a directory"

    def test_src_init_files_exist(self):
        """Verify all __init__.py files exist in src packages."""
        base_path = Path(__file__).parent.parent
        expected_init_files = [
            'src/__init__.py',
            'src/core/__init__.py',
            'src/data/__init__.py',
            'src/strategy/__init__.py',
            'src/execution/__init__.py',
            'src/notification/__init__.py'
        ]

        for init_file in expected_init_files:
            full_path = base_path / init_file
            assert full_path.exists(), f"{init_file} does not exist"
            assert full_path.is_file(), f"{init_file} is not a file"

    def test_test_init_files_exist(self):
        """Verify all __init__.py files exist in test packages."""
        base_path = Path(__file__).parent.parent
        expected_init_files = [
            'tests/__init__.py',
            'tests/unit/__init__.py',
            'tests/integration/__init__.py',
            'tests/fixtures/__init__.py'
        ]

        for init_file in expected_init_files:
            full_path = base_path / init_file
            assert full_path.exists(), f"{init_file} does not exist"
            assert full_path.is_file(), f"{init_file} is not a file"

    def test_python_packages_importable(self):
        """Verify that src packages can be imported."""
        import sys
        base_path = Path(__file__).parent.parent
        sys.path.insert(0, str(base_path))

        # Test importing main package
        try:
            import src
            assert hasattr(src, '__version__'), "src package missing __version__"
        except ImportError as e:
            assert False, f"Cannot import src package: {e}"

        # Test importing subpackages
        subpackages = ['core', 'data', 'strategy', 'execution', 'notification']
        for subpkg in subpackages:
            try:
                module = importlib.import_module(f'src.{subpkg}')
                assert module is not None, f"src.{subpkg} module is None"
            except ImportError as e:
                assert False, f"Cannot import src.{subpkg}: {e}"

    def test_conftest_exists(self):
        """Verify pytest conftest.py exists."""
        base_path = Path(__file__).parent.parent
        conftest = base_path / 'tests' / 'conftest.py'

        assert conftest.exists(), "tests/conftest.py does not exist"
        assert conftest.is_file(), "tests/conftest.py is not a file"

    def test_requirements_dev_exists(self):
        """Verify requirements-dev.txt exists."""
        base_path = Path(__file__).parent.parent
        req_dev = base_path / 'requirements-dev.txt'

        assert req_dev.exists(), "requirements-dev.txt does not exist"
        assert req_dev.is_file(), "requirements-dev.txt is not a file"

        # Verify it contains pytest
        content = req_dev.read_text()
        assert 'pytest' in content, "requirements-dev.txt missing pytest"
        assert 'pytest-asyncio' in content, "requirements-dev.txt missing pytest-asyncio"
        assert 'pytest-cov' in content, "requirements-dev.txt missing pytest-cov"

    def test_logs_directory_writable(self):
        """Verify logs directory is writable."""
        base_path = Path(__file__).parent.parent
        logs_dir = base_path / 'logs'

        # Try to create a test file
        test_file = logs_dir / 'test_write.txt'
        try:
            test_file.write_text('test')
            test_file.unlink()  # Clean up
            success = True
        except Exception:
            success = False

        assert success, "logs/ directory is not writable"
