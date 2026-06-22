"""
Copperhead Debugger

Provides debugging capabilities for validating code before compilation.
Includes syntax checking, type validation, dry-run execution, and more.
"""

import ast
import sys
import traceback
import io
import contextlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class Severity(Enum):
    """Severity of a debug message."""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class DebugMessage:
    """A debug message."""
    severity: Severity
    message: str
    line: Optional[int] = None
    col: Optional[int] = None
    file: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class TypeIssue:
    """A type-related issue."""
    variable: str
    expected: str
    actual: str
    line: int
    message: str


@dataclass
class DebugResult:
    """Result of a debug session."""
    success: bool
    messages: List[DebugMessage] = field(default_factory=list)
    type_issues: List[TypeIssue] = field(default_factory=list)
    execution_output: Optional[str] = None
    execution_error: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class CopperheadDebugger:
    """Debugger for Copperhead code."""
    
    def __init__(self):
        self.warnings: List[DebugMessage] = []
        self.errors: List[DebugMessage] = []
    
    def debug(self, source: str, filename: str = "<string>") -> DebugResult:
        """Run all debug checks on source code."""
        result = DebugResult(success=True)
        
        # 1. Syntax check
        syntax_result = self.check_syntax(source, filename)
        result.messages.extend(syntax_result.messages)
        if not syntax_result.success:
            result.success = False
            return result
        
        # 2. Type validation
        type_result = self.validate_types(source)
        result.messages.extend(type_result.messages)
        result.type_issues.extend(type_result.type_issues)
        
        # 3. Copperhead-specific checks
        ch_result = self.check_copperhead_patterns(source)
        result.messages.extend(ch_result.messages)
        result.suggestions.extend(ch_result.suggestions)
        
        # 4. Dry run (if safe)
        if self._is_safe_to_run(source):
            dry_result = self.dry_run(source)
            result.execution_output = dry_result.execution_output
            result.execution_error = dry_result.execution_error
            result.messages.extend(dry_result.messages)
        
        # Check if there are any errors
        for msg in result.messages:
            if msg.severity in (Severity.ERROR, Severity.CRITICAL):
                result.success = False
                break
        
        return result
    
    def check_syntax(self, source: str, filename: str = "<string>") -> DebugResult:
        """Check Python syntax."""
        result = DebugResult(success=True)
        
        try:
            ast.parse(source, filename=filename)
        except SyntaxError as e:
            result.success = False
            result.messages.append(DebugMessage(
                severity=Severity.CRITICAL,
                message=f"Syntax error: {e.msg}",
                line=e.lineno,
                col=e.offset,
                file=e.filename,
                suggestion=self._suggest_syntax_fix(e)
            ))
        
        return result
    
    def validate_types(self, source: str) -> DebugResult:
        """Validate type annotations."""
        result = DebugResult(success=True)
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return result
        
        # Type mapping for validation
        valid_types = {
            'f32', 'f64', 'i8', 'i16', 'i32', 'i64',
            'u8', 'u16', 'u32', 'u64', 'usize', 'isize',
            'bool', 'str', 'bytes', 'char',
            'list', 'dict', 'set', 'tuple',
            'Option', 'Result', 'Vec', 'HashMap'
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check return type
                if node.returns:
                    type_name = self._extract_type_name(node.returns)
                    if type_name and type_name not in valid_types:
                        if not type_name.startswith(('cp.', 'copperhead.')):
                            result.messages.append(DebugMessage(
                                severity=Severity.WARNING,
                                message=f"Unknown return type: {type_name}",
                                line=node.lineno,
                                suggestion=f"Use a valid Copperhead type like cp.f64, cp.i32, etc."
                            ))
                
                # Check argument types
                for arg in node.args.args:
                    if arg.annotation:
                        type_name = self._extract_type_name(arg.annotation)
                        if type_name and type_name not in valid_types:
                            if not type_name.startswith(('cp.', 'copperhead.')):
                                result.messages.append(DebugMessage(
                                    severity=Severity.WARNING,
                                    message=f"Unknown type for argument '{arg.arg}': {type_name}",
                                    line=node.lineno,
                                    suggestion=f"Use a valid Copperhead type"
                                ))
        
        return result
    
    def check_copperhead_patterns(self, source: str) -> DebugResult:
        """Check for Copperhead-specific patterns and best practices."""
        result = DebugResult(success=True)
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return result
        
        has_copperhead_import = False
        has_compile_decorator = False
        functions_without_types = []
        functions_with_dynamic_fallback = []
        
        for node in ast.walk(tree):
            # Check for copperhead import
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ('copperhead', 'cp'):
                            has_copperhead_import = True
                elif node.module in ('copperhead', 'cp'):
                    has_copperhead_import = True
            
            # Check function definitions
            if isinstance(node, ast.FunctionDef):
                has_type_annotations = False
                has_compile_decorator = False
                
                # Check decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if decorator.attr == 'compile':
                            has_compile_decorator = True
                    elif isinstance(decorator, ast.Name):
                        if decorator.id == 'compile':
                            has_compile_decorator = True
                
                # Check for type annotations
                if node.returns:
                    has_type_annotations = True
                
                for arg in node.args.args:
                    if arg.annotation:
                        has_type_annotations = True
                        break
                
                if not has_type_annotations:
                    functions_without_types.append((node.name, node.lineno))
                
                # Check for dynamic types (untyped lists, dicts)
                for arg in node.args.args:
                    if arg.annotation:
                        type_name = self._extract_type_name(arg.annotation)
                        if type_name in ('list', 'dict', 'set'):
                            functions_with_dynamic_fallback.append(
                                (node.name, arg.arg, type_name, node.lineno)
                            )
        
        # Generate warnings and suggestions
        if not has_copperhead_import:
            result.messages.append(DebugMessage(
                severity=Severity.INFO,
                message="No copperhead import found",
                suggestion="Add 'import copperhead as cp' to use Copperhead features"
            ))
        
        if functions_without_types:
            for func_name, line in functions_without_types:
                result.messages.append(DebugMessage(
                    severity=Severity.WARNING,
                    message=f"Function '{func_name}' lacks type annotations",
                    line=line,
                    suggestion="Add type annotations for better performance"
                ))
        
        if functions_with_dynamic_fallback:
            for func_name, arg_name, type_name, line in functions_with_dynamic_fallback:
                result.messages.append(DebugMessage(
                    severity=Severity.WARNING,
                    message=f"Function '{func_name}' uses dynamic type '{type_name}' for '{arg_name}'",
                    line=line,
                    suggestion=f"Use typed version like {type_name}[cp.f64] for better performance"
                ))
        
        return result
    
    def dry_run(self, source: str) -> DebugResult:
        """Execute code in a sandboxed environment."""
        result = DebugResult(success=True)
        
        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_output = io.StringIO()
        captured_error = io.StringIO()
        
        try:
            sys.stdout = captured_output
            sys.stderr = captured_error
            
            # Create a restricted globals with basic builtins
            safe_globals = {
                '__builtins__': {
                    'print': print,
                    'range': range,
                    'len': len,
                    'int': int,
                    'float': float,
                    'str': str,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'tuple': tuple,
                    'type': type,
                    'isinstance': isinstance,
                    'True': True,
                    'False': False,
                    'None': None,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'sorted': sorted,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                },
            }
            
            # Try to import copperhead if present in source
            if 'import copperhead' in source or 'import cp' in source:
                try:
                    import copperhead as cp
                    safe_globals['cp'] = cp
                    safe_globals['copperhead'] = cp
                except ImportError:
                    pass
            
            # Execute
            exec(compile(source, '<dry-run>', 'exec'), safe_globals)
            
            result.execution_output = captured_output.getvalue()
            
        except Exception as e:
            result.execution_error = f"{type(e).__name__}: {e}"
            result.messages.append(DebugMessage(
                severity=Severity.ERROR,
                message=f"Execution error: {e}",
                suggestion="Check your code for runtime errors"
            ))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        return result
    
    def _is_safe_to_run(self, source: str) -> bool:
        """Check if code is safe to dry-run."""
        dangerous_patterns = [
            'import os',
            'import sys',
            'import subprocess',
            'os.',
            'sys.',
            'subprocess.',
            'open(',
            'exec(',
            'eval(',
            '__import__',
            'globals(',
            'locals(',
        ]
        
        source_lower = source.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in source_lower:
                return False
        
        return True
    
    def _extract_type_name(self, node: ast.expr) -> Optional[str]:
        """Extract type name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Subscript):
            base = self._extract_type_name(node.value)
            return base
        return None
    
    def _suggest_syntax_fix(self, error: SyntaxError) -> str:
        """Suggest a fix for a syntax error."""
        if error.msg == "invalid syntax":
            return "Check for missing colons, parentheses, or quotes"
        elif error.msg == "unexpected EOF while parsing":
            return "Check for missing closing parentheses or colons"
        elif error.msg == "unexpected indent":
            return "Check your indentation (use 4 spaces)"
        elif error.msg == "unindent does not match any outer indentation level":
            return "Check for mixed tabs and spaces"
        return "Review the code around the error location"


class CodeValidator:
    """Validates Copperhead code against best practices."""
    
    def __init__(self):
        self.issues: List[DebugMessage] = []
    
    def validate(self, source: str) -> DebugResult:
        """Validate code and return result."""
        debugger = CopperheadDebugger()
        return debugger.debug(source)
    
    def validate_for_compilation(self, source: str) -> DebugResult:
        """Validate code specifically for compilation."""
        result = self.validate(source)
        
        # Additional compilation-specific checks
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return result
        
        has_rpb = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if decorator.attr == 'compile':
                            has_rpb = True
                    elif isinstance(decorator, ast.Name):
                        if decorator.id == 'compile':
                            has_rpb = True
        
        if not has_rpb:
            result.messages.append(DebugMessage(
                severity=Severity.WARNING,
                message="No Rich Python Blocks found",
                suggestion="Add @cp.compile(target='rust') to functions you want to compile"
            ))
        
        return result
    
    def suggest_improvements(self, source: str) -> List[str]:
        """Suggest improvements for the code."""
        suggestions = []
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ["Fix syntax errors first"]
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for missing type hints
                if not node.returns:
                    suggestions.append(
                        f"Add return type annotation to '{node.name}'"
                    )
                
                # Check for missing docstring
                if not (node.body and isinstance(node.body[0], ast.Expr) 
                       and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    suggestions.append(
                        f"Add docstring to '{node.name}'"
                    )
                
                # Check for large functions
                if len(node.body) > 50:
                    suggestions.append(
                        f"Function '{node.name}' is very long, consider splitting it"
                    )
        
        return suggestions


def debug_source(source: str, filename: str = "<string>") -> DebugResult:
    """Convenience function to debug source code."""
    debugger = CopperheadDebugger()
    return debugger.debug(source, filename)


def validate_source(source: str) -> DebugResult:
    """Convenience function to validate source code."""
    validator = CodeValidator()
    return validator.validate(source)
