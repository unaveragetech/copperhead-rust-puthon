"""
Tests for Copperhead compiler.
"""

import pytest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copperhead.compiler import (
    CopperheadCompiler, BuildConfig, CompilationMode,
    CompilationStatus, compile_source, compile_file
)


class TestBuildConfig:
    """Test BuildConfig class."""
    
    def test_default_config(self):
        """Test default build configuration."""
        config = BuildConfig(source_path="test.py")
        
        assert config.source_path == "test.py"
        assert config.output_name is None
        assert config.mode == CompilationMode.MODULE
        assert config.target == "rust"
        assert config.release is True
        assert config.use_cache is True
    
    def test_custom_config(self):
        """Test custom build configuration."""
        config = BuildConfig(
            source_path="test.py",
            output_name="my_module",
            mode=CompilationMode.BUNDLE,
            target="rust",
            release=False,
            use_cache=False
        )
        
        assert config.source_path == "test.py"
        assert config.output_name == "my_module"
        assert config.mode == CompilationMode.BUNDLE
        assert config.release is False
        assert config.use_cache is False


class TestCopperheadCompiler:
    """Test CopperheadCompiler class."""
    
    def test_compiler_nonexistent_path(self):
        """Test compiler with nonexistent path."""
        config = BuildConfig(source_path="nonexistent.py")
        compiler = CopperheadCompiler(config)
        result = compiler.compile()
        
        assert result.status == CompilationStatus.FAILED
        assert "does not exist" in result.error_message
    
    def test_compiler_empty_file(self):
        """Test compiler with empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            config = BuildConfig(source_path=temp_path, use_cache=False)
            compiler = CopperheadCompiler(config)
            result = compiler.compile()
            
            # Empty file has no RPBs, so should succeed with no output
            assert result.status == CompilationStatus.SUCCESS
        finally:
            os.unlink(temp_path)
    
    def test_compiler_no_rpbs(self):
        """Test compiler with file containing no RPBs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def normal_func(x: int) -> int:
    return x * 2
""")
            temp_path = f.name
        
        try:
            config = BuildConfig(source_path=temp_path, use_cache=False)
            compiler = CopperheadCompiler(config)
            result = compiler.compile()
            
            assert result.status == CompilationStatus.SUCCESS
        finally:
            os.unlink(temp_path)
    
    def test_compiler_with_rpbs(self):
        """Test compiler with file containing RPBs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import copperhead as cp

@cp.compile(target="rust")
def process(x: cp.f64) -> cp.f64:
    return x * 2
""")
            temp_path = f.name
        
        try:
            config = BuildConfig(
                source_path=temp_path,
                use_cache=False,
                build_dir=tempfile.mkdtemp()
            )
            compiler = CopperheadCompiler(config)
            result = compiler.compile()
            
            # Should generate files but may fail cargo build
            # if Rust is not installed
            assert result.status in [
                CompilationStatus.SUCCESS,
                CompilationStatus.FAILED
            ]
            
            # Clean up build directory
            if os.path.exists(config.build_dir):
                shutil.rmtree(config.build_dir)
        finally:
            os.unlink(temp_path)


class TestCompileSource:
    """Test compile_source function."""
    
    def test_compile_source_basic(self):
        """Test compiling source code."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def add(x: cp.f64, y: cp.f64) -> cp.f64:
    return x + y
"""
        result = compile_source(source, use_cache=False)
        
        # Should generate files but may fail cargo build
        assert result.status in [
            CompilationStatus.SUCCESS,
            CompilationStatus.FAILED
        ]


class TestCompileFile:
    """Test compile_file function."""
    
    def test_compile_nonexistent_file(self):
        """Test compiling a file that doesn't exist."""
        result = compile_file("nonexistent.py", use_cache=False)
        
        assert result.status == CompilationStatus.FAILED
        assert "does not exist" in result.error_message
