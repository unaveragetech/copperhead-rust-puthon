"""
Copperhead Rust Transpiler

This module provides functionality to transpile Python AST to Rust code
with PyO3 bindings for seamless Python-Rust interoperability.
"""

import ast
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from .parser import (
    ModuleInfo, FunctionInfo, VariableInfo, TypeInfo,
    TypeKind, parse_source
)


class RustType(Enum):
    """Rust type variants."""
    PRIMITIVE = auto()
    STRING = auto()
    VEC = auto()
    HASHMAP = auto()
    OPTION = auto()
    RESULT = auto()
    TUPLE = auto()
    PYOBJECT = auto()


@dataclass
class RustFunction:
    """Generated Rust function."""
    name: str
    args: List[Tuple[str, str]]  # (name, type)
    return_type: str
    body: str
    no_gil: bool = False
    is_pyfunction: bool = False


@dataclass
class RustModule:
    """Generated Rust module."""
    name: str
    functions: List[RustFunction]
    imports: List[str]
    pyo3_imports: List[str]


class CopperheadTranspiler:
    """Transpiler for converting Python AST to Rust code."""
    
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "
        self.current_function = None
        self.local_vars: Dict[str, str] = {}
        self.pyo3_wrappers: List[str] = []
    
    def transpile_module(self, module_info: ModuleInfo) -> str:
        """Transpile a module to Rust code."""
        lines = []
        
        # Add PyO3 imports
        lines.append("use pyo3::prelude::*;")
        lines.append("use pyo3::types::{PyList, PyDict, PyTuple};")
        lines.append("")
        
        # Add module-level imports based on Python imports
        for imp in module_info.imports:
            if imp == "math":
                lines.append("use std::f64::consts::PI;")
                lines.append("use std::f64::consts::E;")
                lines.append("")
        
        # Transpile each function
        for func in module_info.functions:
            rust_func = self.transpile_function(func)
            if rust_func:
                lines.append(self._generate_rust_function(rust_func))
                lines.append("")
        
        # Add PyO3 module definition
        lines.append("#[pymodule]")
        lines.append("fn _copperhead_module(m: &Bound<'_, PyModule>) -> PyResult<()> {")
        for func in module_info.functions:
            if func.is_rpb:
                lines.append(f"    m.add_function(wrap_pyfunction!({func.name}, m)?)?;")
        lines.append("    Ok(())")
        lines.append("}")
        
        return "\n".join(lines)
    
    def transpile_function(self, func: FunctionInfo) -> Optional[RustFunction]:
        """Transpile a single function to Rust."""
        if not func.is_rpb:
            return None
        
        # Generate argument types
        args = []
        for arg in func.args:
            rust_type = self._python_type_to_rust(arg.type_info)
            args.append((arg.name, rust_type))
        
        # Generate return type
        return_type = "PyResult<PyObject>"
        if func.return_type:
            rust_type = func.return_type.rust_type
            return_type = f"PyResult<{rust_type}>"
        
        # Generate function body (simplified for now)
        body = self._generate_function_body(func)
        
        return RustFunction(
            name=func.name,
            args=args,
            return_type=return_type,
            body=body,
            no_gil=func.no_gil,
            is_pyfunction=True
        )
    
    def _python_type_to_rust(self, type_info: Optional[TypeInfo]) -> str:
        """Convert Python type to Rust type string."""
        if type_info is None:
            return "PyObject"
        
        if type_info.kind == TypeKind.PRIMITIVE:
            return type_info.rust_type
        elif type_info.kind == TypeKind.COLLECTION:
            return type_info.rust_type
        elif type_info.kind == TypeKind.CUSTOM:
            return type_info.rust_type
        else:
            return "PyObject"
    
    def _generate_function_body(self, func: FunctionInfo) -> str:
        """Generate Rust function body."""
        lines = []
        self.indent_level = 1
        
        # For now, generate a placeholder body
        # In a real implementation, this would transpile the Python AST
        lines.append(self._indent("Ok(PyNone::get_bound(py).clone().into()))"))
        
        return "\n".join(lines)
    
    def _generate_rust_function(self, func: RustFunction) -> str:
        """Generate complete Rust function string."""
        lines = []
        
        # Add PyO3 decorator if needed
        if func.is_pyfunction:
            lines.append("#[pyfunction]")
        
        # Generate function signature
        args_str = ", ".join([f"{name}: {rust_type}" for name, rust_type in func.args])
        lines.append(f"fn {func.name}(py: Python<'_>, {args_str}) -> {func.return_type} {{")
        
        # Add function body with proper indentation
        for line in func.body.split("\n"):
            lines.append(self._indent(line))
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _indent(self, line: str) -> str:
        """Add indentation to a line."""
        return self.indent_str * self.indent_level + line
    
    def transpile_expression(self, expr: ast.expr) -> str:
        """Transpile a Python expression to Rust."""
        if isinstance(expr, ast.Name):
            return expr.id
        elif isinstance(expr, ast.Constant):
            return self._transpile_constant(expr)
        elif isinstance(expr, ast.BinOp):
            return self._transpile_binary_op(expr)
        elif isinstance(expr, ast.UnaryOp):
            return self._transpile_unary_op(expr)
        elif isinstance(expr, ast.Call):
            return self._transpile_call(expr)
        elif isinstance(expr, ast.Attribute):
            return self._transpile_attribute(expr)
        elif isinstance(expr, ast.Subscript):
            return self._transpile_subscript(expr)
        elif isinstance(expr, ast.List):
            return self._transpile_list(expr)
        elif isinstance(expr, ast.Dict):
            return self._transpile_dict(expr)
        elif isinstance(expr, ast.Tuple):
            return self._transpile_tuple(expr)
        else:
            return "PyObject::None(py)"
    
    def _transpile_constant(self, expr: ast.Constant) -> str:
        """Transpile a constant value."""
        if isinstance(expr.value, bool):
            return "true" if expr.value else "false"
        elif isinstance(expr.value, int):
            return str(expr.value)
        elif isinstance(expr.value, float):
            return f"{expr.value}f64"
        elif isinstance(expr.value, str):
            return f"PyString::new(py, \"{expr.value}\")"
        elif expr.value is None:
            return "PyNone::get_bound(py).clone()"
        else:
            return "PyObject::None(py)"
    
    def _transpile_binary_op(self, expr: ast.BinOp) -> str:
        """Transpile a binary operation."""
        left = self.transpile_expression(expr.left)
        right = self.transpile_expression(expr.right)
        
        if isinstance(expr.op, ast.Add):
            return f"{left}.add({right})"
        elif isinstance(expr.op, ast.Sub):
            return f"{left}.sub({right})"
        elif isinstance(expr.op, ast.Mult):
            return f"{left}.mul({right})"
        elif isinstance(expr.op, ast.Div):
            return f"{left}.div({right})"
        elif isinstance(expr.op, ast.Mod):
            return f"{left}.remainder({right})"
        elif isinstance(expr.op, ast.Pow):
            return f"{left}.pow({right})"
        else:
            return f"{left} /* unsupported op */ {right}"
    
    def _transpile_unary_op(self, expr: ast.UnaryOp) -> str:
        """Transpile a unary operation."""
        operand = self.transpile_expression(expr.operand)
        
        if isinstance(expr.op, ast.USub):
            return f"{operand}.neg()"
        elif isinstance(expr.op, ast.UAdd):
            return operand
        elif isinstance(expr.op, ast.Not):
            return f"{operand}.not()"
        else:
            return operand
    
    def _transpile_call(self, expr: ast.Call) -> str:
        """Transpile a function call."""
        func_name = self.transpile_expression(expr.func)
        args = [self.transpile_expression(arg) for arg in expr.args]
        args_str = ", ".join(args)
        
        # Handle built-in functions
        if func_name == "len":
            return f"{args[0]}.len()?"
        elif func_name == "range":
            return f"(0..{args[0]})"
        elif func_name == "print":
            return f"println!(\"{{}}\", {args_str})"
        
        return f"{func_name}(py, {args_str})?"
    
    def _transpile_attribute(self, expr: ast.Attribute) -> str:
        """Transpile an attribute access."""
        obj = self.transpile_expression(expr.value)
        attr = expr.attr
        
        # Handle common patterns
        if attr == "sin" or attr == "cos" or attr == "tan":
            return f"{obj}.{attr}()"
        elif attr == "sqrt":
            return f"{obj}.sqrt()"
        elif attr == "abs":
            return f"{obj}.abs()"
        
        return f"{obj}.{attr}"
    
    def _transpile_subscript(self, expr: ast.Subscript) -> str:
        """Transpile a subscript operation."""
        obj = self.transpile_expression(expr.value)
        key = self.transpile_expression(expr.slice)
        
        return f"{obj}.get_item({key})?"
    
    def _transpile_list(self, expr: ast.List) -> str:
        """Transpile a list literal."""
        elements = [self.transpile_expression(elt) for elt in expr.elts]
        elements_str = ", ".join(elements)
        
        return f"vec![{elements_str}]"
    
    def _transpile_dict(self, expr: ast.Dict) -> str:
        """Transpile a dict literal."""
        pairs = []
        for key, value in zip(expr.keys, expr.values):
            k = self.transpile_expression(key)
            v = self.transpile_expression(value)
            pairs.append(f"({k}, {v})")
        
        pairs_str = ", ".join(pairs)
        return f"vec![{pairs_str}].into_iter().collect()"
    
    def _transpile_tuple(self, expr: ast.Tuple) -> str:
        """Transpile a tuple literal."""
        elements = [self.transpile_expression(elt) for elt in expr.elts]
        elements_str = ", ".join(elements)
        
        return f"({elements_str})"


def transpile_module(module_info: ModuleInfo) -> str:
    """Transpile a module to Rust code."""
    transpiler = CopperheadTranspiler()
    return transpiler.transpile_module(module_info)


def transpile_source(source: str, filename: str = "<unknown>") -> str:
    """Transpile Python source code to Rust."""
    module_info = parse_source(source, filename)
    return transpile_module(module_info)


def generate_pyproject_toml(module_name: str) -> str:
    """Generate pyproject.toml for the Rust extension module."""
    return f"""[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "{module_name}"
version = "0.1.0"
description = "Copperhead compiled module"
requires-python = ">=3.8"

[tool.maturin]
features = ["pyo3/extension-module"]
"""


def generate_cargo_toml(module_name: str) -> str:
    """Generate Cargo.toml for the Rust project."""
    return f"""[package]
name = "{module_name}"
version = "0.1.0"
edition = "2021"

[lib]
name = "{module_name}"
crate-type = ["cdylib"]

[dependencies]
pyo3 = {{ version = "0.20.0", features = ["extension-module"] }}
"""


def generate_build_script() -> str:
    """Generate build.py script for compilation."""
    return '''#!/usr/bin/env python3
# Build script for Copperhead compiled modules.

import subprocess
import sys
import os

def build_module(source_file: str, output_name: str):
    """Build a Copperhead module."""
    from copperhead.transpiler import transpile_source, generate_cargo_toml, generate_pyproject_toml
    
    # Read source file
    with open(source_file, 'r') as f:
        source = f.read()
    
    # Transpile to Rust
    rust_code = transpile_source(source, source_file)
    
    # Create build directory
    build_dir = f"build_{output_name}"
    os.makedirs(build_dir, exist_ok=True)
    
    # Write Rust code
    with open(os.path.join(build_dir, "lib.rs"), 'w') as f:
        f.write(rust_code)
    
    # Write Cargo.toml
    with open(os.path.join(build_dir, "Cargo.toml"), 'w') as f:
        f.write(generate_cargo_toml(output_name))
    
    # Build with maturin
    subprocess.run([sys.executable, "-m", "maturin", "build", "--release"], cwd=build_dir)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python build.py <source_file> <output_name>")
        sys.exit(1)
    
    build_module(sys.argv[1], sys.argv[2])
'''
