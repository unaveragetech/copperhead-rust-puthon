"""
Tests for Copperhead transpiler.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copperhead.transpiler import (
    transpile_source, transpile_module, generate_cargo_toml,
    generate_pyproject_toml, generate_build_script
)
from copperhead.parser import parse_source


class TestTranspileSource:
    """Test transpile_source function."""
    
    def test_transpile_simple_function(self):
        """Test transpiling a simple function."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def add(x: cp.f64, y: cp.f64) -> cp.f64:
    return x + y
"""
        rust_code = transpile_source(source)
        
        assert "use pyo3::prelude::*;" in rust_code
        assert "#[pyfunction]" in rust_code
        assert "fn add(" in rust_code
        assert "PyResult<f64>" in rust_code
    
    def test_transpile_with_no_gil(self):
        """Test transpiling a function with no_gil."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
@cp.no_gil
def cpu_intensive(x: cp.f64) -> cp.f64:
    return x * x
"""
        rust_code = transpile_source(source)
        
        assert "#[pyfunction]" in rust_code
        assert "fn cpu_intensive(" in rust_code
    
    def test_transpile_preserves_type_mapping(self):
        """Test that type mappings are preserved."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def func(a: cp.f32, b: cp.i32, c: cp.u64) -> cp.bool:
    return True
"""
        rust_code = transpile_source(source)
        
        assert "a: f32" in rust_code
        assert "b: i32" in rust_code
        assert "c: u64" in rust_code
        assert "PyResult<bool>" in rust_code
    
    def test_transpile_with_math_import(self):
        """Test transpiling with math import."""
        source = """
import copperhead as cp
import math

@cp.compile(target="rust")
def calculate(x: cp.f64) -> cp.f64:
    return x
"""
        rust_code = transpile_source(source)
        
        assert "use std::f64::consts::PI;" in rust_code
    
    def test_transpile_multiple_functions(self):
        """Test transpiling multiple functions."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def func1(x: cp.f64) -> cp.f64:
    return x

@cp.compile(target="rust")
def func2(y: cp.i32) -> cp.i32:
    return y
"""
        rust_code = transpile_source(source)
        
        assert "fn func1(" in rust_code
        assert "fn func2(" in rust_code


class TestTranspileModule:
    """Test transpile_module function."""
    
    def test_transpile_module_basic(self):
        """Test transpiling a module."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def process(x: cp.f64) -> cp.f64:
    return x * 2
"""
        module_info = parse_source(source)
        rust_code = transpile_module(module_info)
        
        assert "use pyo3::prelude::*;" in rust_code
        assert "#[pymodule]" in rust_code
    
    def test_transpile_module_with_rpbs(self):
        """Test transpiling a module with RPBs."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def rpb1(x: cp.f64) -> cp.f64:
    return x

def normal_func(y: int) -> int:
    return y

@cp.compile(target="rust")
def rpb2(z: cp.i32) -> cp.i32:
    return z
"""
        module_info = parse_source(source)
        rust_code = transpile_module(module_info)
        
        assert "fn rpb1(" in rust_code
        assert "fn rpb2(" in rust_code


class TestGenerateCargoToml:
    """Test generate_cargo_toml function."""
    
    def test_generate_cargo_toml(self):
        """Test generating Cargo.toml."""
        cargo_toml = generate_cargo_toml("my_module")
        
        assert '[package]' in cargo_toml
        assert 'name = "my_module"' in cargo_toml
        assert '[lib]' in cargo_toml
        assert 'name = "my_module"' in cargo_toml
        assert '[dependencies]' in cargo_toml
        assert 'pyo3' in cargo_toml


class TestGeneratePyprojectToml:
    """Test generate_pyproject_toml function."""
    
    def test_generate_pyproject_toml(self):
        """Test generating pyproject.toml."""
        pyproject_toml = generate_pyproject_toml("my_module")
        
        assert '[build-system]' in pyproject_toml
        assert 'maturin' in pyproject_toml
        assert '[project]' in pyproject_toml
        assert 'name = "my_module"' in pyproject_toml


class TestGenerateBuildScript:
    """Test generate_build_script function."""
    
    def test_generate_build_script(self):
        """Test generating build script."""
        build_script = generate_build_script()
        
        assert '#!/usr/bin/env python3' in build_script
        assert 'def build_module(' in build_script
        assert 'if __name__ == "__main__":' in build_script
