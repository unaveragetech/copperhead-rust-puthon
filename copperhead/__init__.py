"""
Copperhead: A Granular Transpilation Framework for Seamless Rust-Python Interoperability

Copperhead allows developers to write "rich Python blocks" that can be compiled
to Rust for high-performance execution while remaining fully executable as
standard Python scripts.

Features:
- Rich Python Blocks (RPBs) with Rust-compatible type hints
- Dual compilation modes (module and bundle)
- LLM-powered code generation from natural language
- Automatic test generation
- Interactive code generation mode
"""

import sys
from typing import Any, Callable, TypeVar, Generic, Optional, Union

__version__ = "0.2.0"
__author__ = "Copperhead Team"

# LLM integration (import on demand to avoid requiring ollama)
def _lazy_import_llm():
    """Lazy import LLM module to avoid requiring ollama at import time."""
    from . import llm
    return llm

# Expose LLM classes at module level (but don't import until needed)
llm = _lazy_import_llm

# Type primitives for Rust mapping
f32 = float
f64 = float
i8 = int
i16 = int
i32 = int
i64 = int
u8 = int
u16 = int
u32 = int
u64 = int
usize = int
isize = int
bool = bool
str = str
bytes = bytes
char = str

# Math module with Rust-compatible functions
class MathModule:
    """Math module with Rust-compatible functions."""
    
    @staticmethod
    def sin(x: float) -> float:
        import math
        return math.sin(x)
    
    @staticmethod
    def cos(x: float) -> float:
        import math
        return math.cos(x)
    
    @staticmethod
    def tan(x: float) -> float:
        import math
        return math.tan(x)
    
    @staticmethod
    def sqrt(x: float) -> float:
        import math
        return math.sqrt(x)
    
    @staticmethod
    def pow(x: float, y: float) -> float:
        return x ** y
    
    @staticmethod
    def abs(x: float) -> float:
        return abs(x)
    
    @staticmethod
    def floor(x: float) -> int:
        import math
        return int(math.floor(x))
    
    @staticmethod
    def ceil(x: float) -> int:
        import math
        return int(math.ceil(x))
    
    @staticmethod
    def log(x: float) -> float:
        import math
        return math.log(x)
    
    @staticmethod
    def log2(x: float) -> float:
        import math
        return math.log2(x)
    
    @staticmethod
    def log10(x: float) -> float:
        import math
        return math.log10(x)
    
    @staticmethod
    def min(a: float, b: float) -> float:
        return min(a, b)
    
    @staticmethod
    def max(a: float, b: float) -> float:
        return max(a, b)

math = MathModule()

# Ownership and borrowing types
class MutRef:
    """Mutable reference type for Rust ownership mapping."""
    def __init__(self, value: Any):
        self.value = value
    
    def __repr__(self) -> str:
        return f"MutRef({self.value!r})"

class ImmutRef:
    """Immutable reference type for Rust ownership mapping."""
    def __init__(self, value: Any):
        self.value = value
    
    def __repr__(self) -> str:
        return f"ImmutRef({self.value!r})"

class mut:
    """Mutable type modifier for Rust ownership mapping."""
    def __class_getitem__(cls, item: type) -> type:
        return MutRef
    
    def __init__(self, value: Any = None):
        self.value = value

class ref:
    """Immutable reference type modifier for Rust ownership mapping."""
    def __class_getitem__(cls, item: type) -> type:
        return ImmutRef
    
    def __init__(self, value: Any = None):
        self.value = value

# Collection types
class Vec:
    """Vector type for Rust-compatible dynamic arrays."""
    def __init__(self, items: list = None):
        self.items = items or []
    
    def push(self, item: Any) -> None:
        self.items.append(item)
    
    def pop(self) -> Any:
        return self.items.pop()
    
    def len(self) -> int:
        return len(self.items)
    
    def is_empty(self) -> bool:
        return len(self.items) == 0
    
    def get(self, index: int) -> Any:
        if 0 <= index < len(self.items):
            return self.items[index]
        raise IndexError("Index out of bounds")
    
    def __getitem__(self, index: int) -> Any:
        return self.get(index)
    
    def __setitem__(self, index: int, value: Any) -> None:
        if 0 <= index < len(self.items):
            self.items[index] = value
        else:
            raise IndexError("Index out of bounds")
    
    def __len__(self) -> int:
        return len(self.items)
    
    def __iter__(self):
        return iter(self.items)

class HashMap:
    """Hash map type for Rust-compatible dictionaries."""
    def __init__(self, data: dict = None):
        self._data = data or {}
    
    def insert(self, key: Any, value: Any) -> None:
        self._data[key] = value
    
    def get(self, key: Any) -> Any:
        return self._data.get(key)
    
    def remove(self, key: Any) -> Any:
        return self._data.pop(key, None)
    
    def contains_key(self, key: Any) -> bool:
        return key in self._data
    
    def len(self) -> int:
        return len(self._data)
    
    def is_empty(self) -> bool:
        return len(self._data) == 0
    
    def keys(self) -> list:
        return list(self._data.keys())
    
    def values(self) -> list:
        return list(self._data.values())
    
    def items(self) -> list:
        return list(self._data.items())
    
    def __getitem__(self, key: Any) -> Any:
        return self.get(key)
    
    def __setitem__(self, key: Any, value: Any) -> None:
        self.insert(key, value)
    
    def __len__(self) -> int:
        return len(self._data)
    
    def __contains__(self, key: Any) -> bool:
        return self.contains_key(key)

# Option type for nullable values
class Option:
    """Option type for Rust-compatible nullable values."""
    def __init__(self, value: Any = None):
        self.value = value
    
    def is_some(self) -> bool:
        return self.value is not None
    
    def is_none(self) -> bool:
        return self.value is None
    
    def unwrap(self) -> Any:
        if self.value is None:
            raise ValueError("Called unwrap on None value")
        return self.value
    
    def unwrap_or(self, default: Any) -> Any:
        return self.value if self.value is not None else default
    
    def map(self, f: Callable) -> 'Option':
        if self.value is not None:
            return Option(f(self.value))
        return Option(None)
    
    def __repr__(self) -> str:
        return f"Some({self.value!r})" if self.is_some() else "None"

# Result type for error handling
class Result:
    """Result type for Rust-compatible error handling."""
    def __init__(self, value: Any = None, error: Any = None):
        self.value = value
        self.error = error
    
    def is_ok(self) -> bool:
        return self.error is None
    
    def is_err(self) -> bool:
        return self.error is not None
    
    def unwrap(self) -> Any:
        if self.error is not None:
            raise RuntimeError(f"Called unwrap on error: {self.error}")
        return self.value
    
    def unwrap_or(self, default: Any) -> Any:
        return self.value if self.error is None else default
    
    def map(self, f: Callable) -> 'Result':
        if self.error is None:
            try:
                return Result(value=f(self.value))
            except Exception as e:
                return Result(error=e)
        return Result(error=self.error)
    
    def __repr__(self) -> str:
        if self.is_ok():
            return f"Ok({self.value!r})"
        return f"Err({self.error!r})"

def Ok(value: Any) -> Result:
    """Create a successful Result."""
    return Result(value=value)

def Err(error: Any) -> Result:
    """Create an error Result."""
    return Result(error=error)

# Decorators for compilation ------------------------------------------------
from .jit import (  # noqa: E402
    jit, JitFunction, CopperheadWarning, Unsupported, BuildError,
    rust_available, clear_cache, cache_dir,
)


def compile(func=None, *, target: str = "rust", strict: bool = False, warn: bool = True,
            eager: bool = False):
    """Compile a function to native Rust.  All of these forms work::

        @cp.compile
        @cp.compile()
        @cp.compile("rust")
        @cp.compile(strict=True)

    The first call compiles (result cached on disk); unsupported code falls back
    to Python with a single warning.  See :func:`copperhead.jit`.
    """
    if isinstance(func, str):  # legacy: @cp.compile("rust")
        target, func = func, None
    if target != "rust":
        raise ValueError(f"unsupported target {target!r} (only 'rust')")

    def decorator(f: Callable) -> Callable:
        if isinstance(f, JitFunction):
            return f
        jf = JitFunction(f, strict=strict, warn=warn, eager=eager)
        jf._copperhead_target = target
        return jf

    return decorator(func) if callable(func) else decorator


def no_gil(func: Callable) -> Callable:
    """Compile ``func`` and mark it GIL-free.

    Compiled functions are called through ctypes, which releases the GIL for the
    whole native call, so several Python threads really do run them in parallel.
    """
    if isinstance(func, JitFunction):
        func._no_gil = func._copperhead_no_gil = True
        return func
    return JitFunction(func, no_gil=True)


# Import hook (opt-in) ---------------------------------------------------------
import importlib.abc as _abc  # noqa: E402
import importlib.machinery as _machinery  # noqa: E402
import importlib.util as _util  # noqa: E402


class CopperheadImporter(_abc.MetaPathFinder):
    """Meta-path finder for modules registered with :meth:`register` only.

    It never claims a module it does not know about, so it cannot interfere with
    normal imports.  Registered paths must be compiled extension modules
    (``.pyd`` / ``.so``) built by ``copperhead build``.
    """

    def __init__(self):
        self.modules: dict = {}

    def register(self, fullname: str, path: str) -> None:
        self.modules[fullname] = path

    def find_spec(self, fullname, path=None, target=None):
        file = self.modules.get(fullname)
        if file is None:
            return None
        loader = _machinery.ExtensionFileLoader(fullname, file)
        return _util.spec_from_file_location(fullname, file, loader=loader)


_importer = CopperheadImporter()


def install_importer() -> CopperheadImporter:
    """Install the (idempotent) import hook. Not done automatically."""
    if _importer not in sys.meta_path:
        sys.meta_path.append(_importer)
    return _importer


def uninstall_importer() -> None:
    if _importer in sys.meta_path:
        sys.meta_path.remove(_importer)


# Utility functions
def sizeof(obj: Any) -> int:
    """Get size of object in bytes."""
    import sys
    return sys.getsizeof(obj)

def type_name(obj: Any) -> str:
    """Get type name of object."""
    return type(obj).__name__

def assert_type(obj: Any, expected_type: type) -> None:
    """Assert that object is of expected type."""
    if not isinstance(obj, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(obj).__name__}")
