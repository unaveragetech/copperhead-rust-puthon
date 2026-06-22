"""
Tests for Copperhead CLI.
"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copperhead.cli import (
    main, cmd_build, cmd_lint, cmd_transpile, cmd_check, cmd_cache
)


class TestCLI:
    """Test CLI functionality."""
    
    def test_main_no_args(self):
        """Test main with no arguments."""
        # Should print help (no SystemExit raised when no args)
        sys.argv = ["copperhead"]
        main()  # Should not raise, just prints help
    
    def test_main_version(self):
        """Test main with --version."""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["copperhead", "--version"]
            main()
        assert exc_info.value.code == 0
    
    def test_build_nonexistent(self):
        """Test build command with nonexistent file."""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["copperhead", "build", "nonexistent.py"]
            main()
        assert exc_info.value.code == 1
    
    def test_lint_nonexistent(self):
        """Test lint command with nonexistent file."""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["copperhead", "lint", "nonexistent.py"]
            main()
        assert exc_info.value.code == 1
    
    def test_transpile_nonexistent(self):
        """Test transpile command with nonexistent file."""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["copperhead", "transpile", "nonexistent.py"]
            main()
        assert exc_info.value.code == 1
    
    def test_check_nonexistent(self):
        """Test check command with nonexistent file."""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["copperhead", "check", "nonexistent.py"]
            main()
        assert exc_info.value.code == 1


class TestLint:
    """Test lint functionality."""
    
    def test_lint_file_with_typed_rpb(self):
        """Test linting a well-typed RPB."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import copperhead as cp

@cp.compile(target="rust")
def process(data: list[cp.f64]) -> cp.f64:
    return 0.0
""")
            temp_path = f.name
        
        try:
            # Should not print any warnings
            sys.argv = ["copperhead", "lint", temp_path]
            main()
        finally:
            os.unlink(temp_path)
    
    def test_lint_file_with_untyped_rpb(self):
        """Test linting an untyped RPB."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import copperhead as cp

@cp.compile(target="rust")
def process(data):
    return 0.0
""")
            temp_path = f.name
        
        try:
            # Should print warnings about missing types
            sys.argv = ["copperhead", "lint", temp_path]
            main()
        finally:
            os.unlink(temp_path)


class TestTranspile:
    """Test transpile functionality."""
    
    def test_transpile_to_stdout(self):
        """Test transpiling to stdout."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import copperhead as cp

@cp.compile(target="rust")
def add(x: cp.f64, y: cp.f64) -> cp.f64:
    return x + y
""")
            temp_path = f.name
        
        try:
            sys.argv = ["copperhead", "transpile", temp_path]
            main()
        finally:
            os.unlink(temp_path)
    
    def test_transpile_to_file(self):
        """Test transpiling to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import copperhead as cp

@cp.compile(target="rust")
def add(x: cp.f64, y: cp.f64) -> cp.f64:
    return x + y
""")
            temp_path = f.name
        
        output_file = temp_path.replace('.py', '.rs')
        
        try:
            sys.argv = ["copperhead", "transpile", temp_path, "-o", output_file]
            main()
            
            assert os.path.exists(output_file)
        finally:
            os.unlink(temp_path)
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestCheck:
    """Test check functionality."""
    
    def test_check_valid_python(self):
        """Test checking valid Python syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def func(): pass")
            temp_path = f.name
        
        try:
            sys.argv = ["copperhead", "check", temp_path]
            main()
        finally:
            os.unlink(temp_path)
    
    def test_check_invalid_python(self):
        """Test checking invalid Python syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def func(: pass")
            temp_path = f.name
        
        try:
            sys.argv = ["copperhead", "check", temp_path]
            main()
        finally:
            os.unlink(temp_path)


class TestCache:
    """Test cache functionality."""
    
    def test_cache_show_empty(self):
        """Test showing empty cache."""
        sys.argv = ["copperhead", "cache", "show"]
        main()
    
    def test_cache_size_empty(self):
        """Test showing size of empty cache."""
        sys.argv = ["copperhead", "cache", "size"]
        main()
    
    def test_cache_clean(self):
        """Test cleaning cache."""
        sys.argv = ["copperhead", "cache", "clean"]
        main()
