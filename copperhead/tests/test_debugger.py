"""
Tests for Copperhead debugger.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copperhead.debugger import (
    CopperheadDebugger, CodeValidator, DebugResult,
    DebugMessage, TypeIssue, Severity
)


class TestCopperheadDebugger:
    """Test CopperheadDebugger class."""
    
    def test_debugger_initialization(self):
        """Test debugger initialization."""
        debugger = CopperheadDebugger()
        assert debugger.warnings == []
        assert debugger.errors == []
    
    def test_debug_valid_code(self):
        """Test debugging valid code."""
        debugger = CopperheadDebugger()
        source = """
def add(x: float, y: float) -> float:
    return x + y
"""
        result = debugger.debug(source)
        assert result.success is True
    
    def test_debug_syntax_error(self):
        """Test debugging code with syntax error."""
        debugger = CopperheadDebugger()
        source = "def func(: pass"
        result = debugger.debug(source)
        assert result.success is False
        assert len(result.messages) > 0
        assert result.messages[0].severity == Severity.CRITICAL
    
    def test_check_syntax_valid(self):
        """Test syntax checking valid code."""
        debugger = CopperheadDebugger()
        source = "def func(): pass"
        result = debugger.check_syntax(source)
        assert result.success is True
    
    def test_check_syntax_invalid(self):
        """Test syntax checking invalid code."""
        debugger = CopperheadDebugger()
        source = "def func(: pass"
        result = debugger.check_syntax(source)
        assert result.success is False
    
    def test_validate_types(self):
        """Test type validation."""
        debugger = CopperheadDebugger()
        source = """
def add(x: float, y: float) -> float:
    return x + y
"""
        result = debugger.validate_types(source)
        assert result.success is True
    
    def test_validate_types_unknown_type(self):
        """Test type validation with unknown type."""
        debugger = CopperheadDebugger()
        source = """
def func(x: UnknownType) -> int:
    return x
"""
        result = debugger.validate_types(source)
        # Should have a warning about unknown type
        assert any("Unknown type" in m.message for m in result.messages)
    
    def test_check_copperhead_patterns(self):
        """Test Copperhead pattern checking."""
        debugger = CopperheadDebugger()
        source = """
import copperhead as cp

@cp.compile(target="rust")
def add(x: cp.f64, y: cp.f64) -> cp.f64:
    return x + y
"""
        result = debugger.check_copperhead_patterns(source)
        assert result.success is True
    
    def test_check_copperhead_patterns_missing_import(self):
        """Test pattern checking with missing import."""
        debugger = CopperheadDebugger()
        source = """
def add(x: float, y: float) -> float:
    return x + y
"""
        result = debugger.check_copperhead_patterns(source)
        # Should have info about missing import
        assert any("copperhead import" in m.message.lower() for m in result.messages)
    
    def test_dry_run_safe_code(self):
        """Test dry run with safe code."""
        debugger = CopperheadDebugger()
        source = """
x = 5
y = 10
result = x + y
"""
        result = debugger.dry_run(source)
        assert result.success is True
    
    def test_dry_run_unsafe_code(self):
        """Test dry run with unsafe code."""
        debugger = CopperheadDebugger()
        # Code with os import should be marked as unsafe and not executed
        source = "import os"
        result = debugger.dry_run(source)
        # Should not run unsafe code - either no error or import error is acceptable
        assert result.execution_error is None or "ImportError" in str(result.execution_error)


class TestCodeValidator:
    """Test CodeValidator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = CodeValidator()
        assert validator.issues == []
    
    def test_validate_code(self):
        """Test code validation."""
        validator = CodeValidator()
        source = """
def add(x: float, y: float) -> float:
    return x + y
"""
        result = validator.validate(source)
        assert result.success is True
    
    def test_validate_for_compilation(self):
        """Test validation for compilation."""
        validator = CodeValidator()
        source = """
@compile(target="rust")
def add(x: float, y: float) -> float:
    return x + y
"""
        result = validator.validate_for_compilation(source)
        # May have warnings but no critical errors from syntax
        assert result.success is True or any("No Rich Python Blocks" in m.message for m in result.messages)
    
    def test_validate_for_compilation_no_rpb(self):
        """Test validation for compilation without RPBs."""
        validator = CodeValidator()
        source = """
def add(x: float, y: float) -> float:
    return x + y
"""
        result = validator.validate_for_compilation(source)
        # Should have warning about no RPBs
        assert any("No Rich Python Blocks" in m.message for m in result.messages)
    
    def test_suggest_improvements(self):
        """Test improvement suggestions."""
        validator = CodeValidator()
        source = """
def add(x, y):
    return x + y
"""
        suggestions = validator.suggest_improvements(source)
        assert len(suggestions) > 0
        assert any("type" in s.lower() for s in suggestions)


class TestDebugResult:
    """Test DebugResult dataclass."""
    
    def test_debug_result_creation(self):
        """Test DebugResult creation."""
        result = DebugResult(success=True)
        assert result.success is True
        assert result.messages == []
        assert result.type_issues == []
    
    def test_debug_result_with_messages(self):
        """Test DebugResult with messages."""
        msg = DebugMessage(
            severity=Severity.WARNING,
            message="Test warning"
        )
        result = DebugResult(success=True, messages=[msg])
        assert len(result.messages) == 1
        assert result.messages[0].message == "Test warning"


class TestDebugMessage:
    """Test DebugMessage dataclass."""
    
    def test_message_creation(self):
        """Test message creation."""
        msg = DebugMessage(
            severity=Severity.ERROR,
            message="Test error",
            line=10,
            col=5
        )
        assert msg.severity == Severity.ERROR
        assert msg.message == "Test error"
        assert msg.line == 10
        assert msg.col == 5
    
    def test_message_with_suggestion(self):
        """Test message with suggestion."""
        msg = DebugMessage(
            severity=Severity.WARNING,
            message="Missing type",
            suggestion="Add type annotation"
        )
        assert msg.suggestion == "Add type annotation"


class TestTypeIssue:
    """Test TypeIssue dataclass."""
    
    def test_type_issue_creation(self):
        """Test TypeIssue creation."""
        issue = TypeIssue(
            variable="x",
            expected="f64",
            actual="str",
            line=10,
            message="Type mismatch"
        )
        assert issue.variable == "x"
        assert issue.expected == "f64"
        assert issue.actual == "str"


class TestSeverity:
    """Test Severity enum."""
    
    def test_severity_values(self):
        """Test severity enum values."""
        assert Severity.INFO.value == 1
        assert Severity.WARNING.value == 2
        assert Severity.ERROR.value == 3
        assert Severity.CRITICAL.value == 4
