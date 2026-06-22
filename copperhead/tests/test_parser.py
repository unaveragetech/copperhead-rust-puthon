"""
Tests for Copperhead parser.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copperhead.parser import (
    parse_source, parse_file, find_rpbs, is_rpb,
    extract_type_info, TypeKind
)


class TestParser:
    """Test parser functionality."""
    
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        source = """
def add(x: int, y: int) -> int:
    return x + y
"""
        module = parse_source(source)
        assert len(module.functions) == 1
        assert module.functions[0].name == "add"
        assert len(module.functions[0].args) == 2
    
    def test_parse_rpb_function(self):
        """Test parsing a Rich Python Block."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def process_data(data: list[cp.f64]) -> cp.f64:
    total: cp.f64 = 0.0
    for val in data:
        total += val
    return total
"""
        module = parse_source(source)
        assert module.rpb_count == 1
        assert module.functions[0].is_rpb is True
    
    def test_parse_no_gil_function(self):
        """Test parsing a function with no_gil decorator."""
        source = """
import copperhead as cp

@cp.no_gil
def cpu_intensive(x: cp.f64) -> cp.f64:
    return x * x
"""
        module = parse_source(source)
        assert len(module.functions) == 1
        assert module.functions[0].no_gil is True
    
    def test_parse_ownership_types(self):
        """Test parsing ownership types."""
        source = """
import copperhead as cp

def mutate_state(state: cp.mut[State], ref_data: cp.ref[Data]):
    pass
"""
        module = parse_source(source)
        func = module.functions[0]
        assert func.args[0].is_mutable is True
        assert func.args[1].is_reference is True
    
    def test_parse_collection_types(self):
        """Test parsing collection types."""
        source = """
import copperhead as cp

def process(items: list[cp.f64], mapping: dict[str, cp.i32]) -> list[cp.f64]:
    return items
"""
        module = parse_source(source)
        func = module.functions[0]
        assert func.args[0].type_info is not None
        assert func.args[0].type_info.kind == TypeKind.COLLECTION
    
    def test_parse_multiple_functions(self):
        """Test parsing multiple functions."""
        source = """
def func1(x: int) -> int:
    return x

def func2(y: str) -> str:
    return y

def func3(z: float) -> float:
    return z
"""
        module = parse_source(source)
        assert len(module.functions) == 3
    
    def test_parse_imports(self):
        """Test parsing imports."""
        source = """
import os
import sys
from pathlib import Path
import copperhead as cp
"""
        module = parse_source(source)
        assert "os" in module.imports
        assert "sys" in module.imports
        assert "pathlib" in module.imports
        assert "copperhead" in module.imports
    
    def test_parse_primitives(self):
        """Test parsing primitive types."""
        source = """
import copperhead as cp

def func(a: cp.f32, b: cp.f64, c: cp.i32, d: cp.u64) -> cp.bool:
    return True
"""
        module = parse_source(source)
        func = module.functions[0]
        
        assert func.args[0].type_info.rust_type == "f32"
        assert func.args[1].type_info.rust_type == "f64"
        assert func.args[2].type_info.rust_type == "i32"
        assert func.args[3].type_info.rust_type == "u64"
        assert func.return_type.rust_type == "bool"


class TestFindRPBs:
    """Test finding Rich Python Blocks."""
    
    def test_find_rpbs_basic(self):
        """Test finding RPBs in basic source."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def rpb_func(x: cp.f64) -> cp.f64:
    return x * 2

def normal_func(x: int) -> int:
    return x
"""
        rpbs = find_rpbs(source)
        assert len(rpbs) == 1
        assert rpbs[0].name == "rpb_func"
    
    def test_find_rpbs_none(self):
        """Test finding RPBs when none exist."""
        source = """
def func1(x: int) -> int:
    return x

def func2(y: str) -> str:
    return y
"""
        rpbs = find_rpbs(source)
        assert len(rpbs) == 0
    
    def test_find_rpbs_multiple(self):
        """Test finding multiple RPBs."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def rpb1(x: cp.f64) -> cp.f64:
    return x

@cp.compile(target="rust")
def rpb2(y: cp.i32) -> cp.i32:
    return y
"""
        rpbs = find_rpbs(source)
        assert len(rpbs) == 2


class TestIsRPB:
    """Test is_rpb function."""
    
    def test_is_rpb_true(self):
        """Test is_rpb returns True for RPB."""
        source = """
import copperhead as cp

@cp.compile(target="rust")
def my_func(x: cp.f64) -> cp.f64:
    return x
"""
        assert is_rpb(source) is True
    
    def test_is_rpb_false(self):
        """Test is_rpb returns False for normal function."""
        source = """
def my_func(x: int) -> int:
    return x
"""
        assert is_rpb(source) is False


class TestExtractTypeInfo:
    """Test extract_type_info function."""
    
    def test_extract_basic_types(self):
        """Test extracting basic type information."""
        source = """
import copperhead as cp

def func(a: cp.f64, b: cp.i32) -> cp.bool:
    return True
"""
        type_info = extract_type_info(source)
        assert "a" in type_info
        assert "b" in type_info
        assert "func_return" in type_info
    
    def test_extract_no_types(self):
        """Test extracting when no types are specified."""
        source = """
def func(a, b):
    return a
"""
        type_info = extract_type_info(source)
        assert len(type_info) == 0


class TestParseFile:
    """Test parse_file function."""
    
    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parse_file("nonexistent.py")
