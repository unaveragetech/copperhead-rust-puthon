# `@cp.jit` guide

```python
import copperhead as cp

@cp.jit
def dot(a, b):
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s

dot([1.0, 2.0], [3.0, 4.0])   # 11.0, computed in native Rust
```

## Install
`pip install copperhead-rust-puthon` (Python 3.9+) and install Rust from <https://rustup.rs> so `rustc` is on PATH.
No `rustc`? Code still runs, as plain Python.

## Lifecycle of a call
1. Arguments are classified: `int`, `float`, `bool`, non-empty `list` of int or float, `array.array('q'|'d')`, 1-D C-contiguous numpy `int64`/`float64`.
2. The function is specialised on those types (one native build per type combination).
3. Rust source is generated, compiled with `rustc -O` into a shared library and cached by content hash.
4. The library is loaded with `ctypes` and called with the GIL released.
5. If anything is unsupported or goes wrong the *original Python function* runs instead.

## Decorators
| form | effect |
|---|---|
| `@cp.jit`, `@cp.compile` (also with `()`) | compile on first call |
| `@cp.jit(strict=True)` | raise `cp.Unsupported` rather than fall back |
| `@cp.jit(warn=False)` | no fallback warning |
| `@cp.jit(eager=True)` | compile at decoration time if all parameters are annotated |
| `@cp.no_gil` | compile + mark thread-safe (native calls already release the GIL) |

## What compiles
- Scalars `int` (checked i64), `float` (f64), `bool`.
- `if/elif/else`, `while`, `for i in range(...)`, `for x in some_list`, `break`, `continue`, ternaries.
- `+ - * / // % **`, bit ops, shifts, comparisons (chained too), `not`, `and`/`or` between bools.
- Local lists: `[0] * n`, `[1, 2, 3]`, `x: list[int] = []`, `append`, `x[i]`, `x[i] = v`, `len`.
- `abs min max int float bool len sum(int list)` and `math.sqrt sin cos tan asin acos atan atan2 exp log log2 log10 floor ceil fabs hypot isnan isinf pi e tau`.
- Calls to other plain or decorated functions (compiled into the same library); recursion (add `-> int` for mutual recursion).
- Module-level numeric constants (inlined; if you change one later the compiled version is bypassed).

## What falls back to Python (with one warning)
strings, dicts, sets, tuples as values, classes, comprehensions, `try`, `with`, `print`/I/O, `isinstance`, generators,
`async`, `float` sums via `sum()`, mixed `int`/`float` variables (`x = 0` then `x += 0.5` - write `x = 0.0`),
`a and b` between non-bools, mutating list arguments.

## Exactness notes
- Integers beyond 64 bits: the native call reports overflow and Python recomputes the exact big int.
- Zero division, bad index, math domain errors: Python re-runs the call and raises the genuine exception.
- Compiled functions must be pure because failed native calls are re-run in Python.
- Comparing `int` with `float` is only compiled when the int is a small literal.

## Debugging
```python
f.explain(3, 4.5)       # 'compiled to Rust (int, float)'  or  'runs in Python: <reason>'
print(f.rust_source(3, 4.5))
f.py_func(3, 4.5)       # original function
f.native_calls, f.python_calls
```
Env vars: `COPPERHEAD_DISABLE=1` (never compile), `COPPERHEAD_CACHE=dir`, `RUSTC=path`.

## Benchmarks
`python benchmarks/jit_bench.py` (compile time excluded, results compared with Python).
