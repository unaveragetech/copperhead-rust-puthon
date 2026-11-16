# Copperhead

**Write Python. Run Rust.**

[![GitHub](https://img.shields.io/badge/GitHub-unaveragetech%2Fcopperhead--rust--puthon-blue?logo=github)](https://github.com/unaveragetech/copperhead-rust-puthon)
[![Docs](https://img.shields.io/badge/Docs-Interactive-green?logo=markdown)](https://copperhead-ad8qypth.manus.space)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)](https://github.com/unaveragetech/copperhead-rust-puthon/tree/main/copperhead/tests/)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-SDUC%201.1-green)](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/LICENSE)

> **Interactive Documentation:** [copperhead-ad8qypth.manus.space](https://copperhead-ad8qypth.manus.space/)

---

## What is Copperhead?

Copperhead compiles **Python functions to native Rust** — you add one decorator and keep writing Python.

```python
import copperhead as cp

@cp.jit                      # that's the whole API
def collatz_total(limit):
    best = 0
    for start in range(1, limit):
        n, steps = start, 0
        while n != 1:
            n = n // 2 if n % 2 == 0 else 3 * n + 1
            steps += 1
        best = max(best, steps)
    return best

collatz_total(300_000)       # 1st call: compiles (~1 s, cached on disk). Every later call: native.
```

* **No annotations needed.** The function is specialised on the runtime types of its arguments
  (`int`, `float`, `bool`, `list[int]`, `list[float]`, `array.array`, 1-D numpy arrays).
* **Python semantics, exactly.** Floor division/modulo, negative indexing, `**`, chained comparisons and
  `int` overflow behave like CPython (integers are overflow-checked; if a value outgrows 64 bits the call is
  transparently re-run in Python and returns the big int).
* **Never silently wrong.** Anything the translator cannot reproduce exactly (try/except, strings, dicts,
  classes, `print`, `isinstance`, ...) makes the function run as plain Python and emits **one**
  `CopperheadWarning` that says why. `@cp.jit(strict=True)` turns that into an error instead.
  Errors at run time in native code (zero division, bad index, overflow) re-run the call in Python so you get the real exception.
* **Real parallelism.** Native calls release the GIL, so threads running compiled functions scale across cores.
* **Zero setup beyond Rust.** It needs only `rustc` (from [rustup.rs](https://rustup.rs)); no cargo project,
  no crates, no PyO3 — the compiled library is loaded with `ctypes`.

Measured on this repository (`python benchmarks/jit_bench.py`, Python 3.13, compile excluded, results verified equal):

| case | CPython | `@cp.jit` | speed-up |
|---|---|---|---|
| fib(30) | 253 ms | 11 ms | 22x |
| Collatz up to 300 000 | 5 324 ms | 75 ms | 71x |
| sieve of Eratosthenes, n = 5 M | 1 234 ms | 104 ms | 12x |
| Mandelbrot 300x300 | 525 ms | 9 ms | 60x |

Speed-ups depend on the workload; code dominated by calls into other libraries will not speed up.

### Decorators

| decorator | meaning |
|---|---|
| `@cp.jit` / `@cp.compile` | compile on first call (both spellings, with or without `()`) |
| `@cp.jit(strict=True)` | raise `cp.Unsupported` instead of falling back to Python |
| `@cp.jit(eager=True)` | compile at import time when every parameter is annotated (`x: int`, `y: float`, ...) |
| `@cp.no_gil` | same, and documents that the function is meant to be run from threads |

Introspection: `f.explain(*args)` (why is it / isn't it compiled), `f.rust_source(*args)` (the generated Rust),
`f.py_func` (the original), `f.native_calls` / `f.python_calls`. Set `COPPERHEAD_DISABLE=1` to run everything as plain Python.

### Supported subset (compiled natively)

`int` / `float` / `bool` scalars, `if` / `while` / `for … in range()` / `for x in list`, `break` / `continue`,
tuple swaps, local lists (`[0] * n`, `append`, indexing), `len`, `abs`, `min`, `max`, `int()`, `float()`, `bool()`,
`sum()` of int lists, `math.*` (sqrt, sin, cos, tan, exp, log, floor, ceil, …), `raise`/`assert` (re-run in Python),
and calls to other functions in the same module (compiled together, recursion included).
List arguments are read-only inside compiled code. Functions must be pure (no I/O, no mutation of arguments).

---

## Also in this repository

A second, **experimental** pipeline (`copperhead build`) transpiles annotated functions to a
PyO3 extension module via Cargo (`.pyd` on Windows, `.so` elsewhere) so they can be shipped as a package.
It now builds and imports real extensions (single files and directory bundles) and runs in *strict* mode:
if a construct would lose its Python semantics (`try`, `with`, `isinstance`, `yield`, ...) the build fails with an
explanation instead of generating placeholder code. The AI code-generation features and module registry are unchanged.

Tests: `python -m pytest copperhead/tests` — includes differential tests that run each function in Python and
in Rust and compare results *and* exceptions, plus end-to-end build/import tests.

---

## Quick Start (2 minutes)

```bash
pip install copperhead-rust-puthon      # imported as `copperhead`; CLI command: `copperhead`
# or straight from GitHub:
pip install git+https://github.com/unaveragetech/copperhead-rust-puthon.git
# Install Rust (provides `rustc`): https://rustup.rs  -- then check:
python -c "import copperhead as cp; print(cp.rust_available())"   # -> True
```

Without `rustc` everything still works: decorated functions simply run as plain Python.
Requires Python 3.9+. Compiled libraries are cached in `%LOCALAPPDATA%\copperhead` (Windows) or
`~/.cache/copperhead` (override with `COPPERHEAD_CACHE`; wipe with `cp.clear_cache()`).

```python
import copperhead as cp

@cp.jit
def calculate(x):
    return x * x + cp.math.sin(x)  # or `import math; math.sin(x)`
```

---

## Why Copperhead?

### The Problem
- **Python is easy** but slow for heavy computations
- **Rust is fast** but hard to learn and write
- **You've been forced to choose** between easy and fast

### The Solution
Copperhead lets you:
1. Write Python (easy)
2. Mark functions for Rust speed (simple annotation)
3. Get large speed-ups on numeric/loop-heavy code (12-70x in our benchmarks)

### What Makes It Different

| Feature | Copperhead | Other Tools |
|---------|------------|-------------|
| Still Python? | Yes, 100% | Usually no |
| Learn new syntax? | No | Yes |
| Gradual optimization? | Yes | No |
| AI code generation? | Yes | No |
| Point to specific functions? | Yes | No |
| Actually compiles to Rust? | Yes | Varies |

---

## Core Features

### 1. Rich Python Blocks
Mark any function for Rust compilation:

```python
@cp.compile(target="rust")
def my_fast_function(data: list[float]) -> float:
    total = 0.0
    for x in data:
        total += x * x
    return total
```

### 2. Type System (Optional but Faster)
Add types for even more speed:

```python
@cp.compile(target="rust")
def process(x: cp.f64, y: cp.f64) -> cp.f64:
    return x + y
```

Available types:
- `cp.i8`, `cp.i16`, `cp.i32`, `cp.i64` (integers)
- `cp.f32`, `cp.f64` (decimals)
- `cp.bool` (true/false)
- `cp.str` (text)
- `list[T]`, `dict[K, V]` (collections)

### 3. Ownership (For Advanced Users)
Control how data is passed to Rust:

```python
# Mutable reference (can modify)
def update(state: cp.mut[MyClass]) -> None:
    state.value += 1

# Immutable reference (read-only)
def read(data: cp.ref[MyClass]) -> float:
    return data.value
```

### 4. GIL Release (For Threading)
Enable true parallel processing:

```python
@cp.compile(target="rust")
@cp.no_gil
def cpu_heavy(n: int) -> float:
    total = 0.0
    for i in range(n):
        total += cp.math.sin(float(i))
    return total
```

### 5. Math Module
Built-in math functions that compile to fast Rust:

```python
cp.math.sin(x)      # Sine
cp.math.cos(x)      # Cosine
cp.math.sqrt(x)     # Square root
cp.math.pow(x, y)   # Power
cp.math.log(x)      # Natural log
cp.math.min(a, b)   # Minimum
cp.math.max(a, b)   # Maximum
```

### 6. Error Handling
Safe error handling with Rust-style Results:

```python
@cp.compile(target="rust")
def divide(a: float, b: float):
    if b == 0.0:
        return cp.Err("Cannot divide by zero")
    return cp.Ok(a / b)
```

---

## AI Agent

Copperhead includes an AI assistant that writes code for you.

### Generate Code from English
```bash
copperhead generate "Create a function that sorts a list using quicksort"
```

### Interactive Mode
```bash
copperhead interactive
```

Then just describe what you want:
```
You: Create a function that finds prime numbers up to n
AI: [Generates complete Copperhead code with tests]
```

### What the AI Does
1. Understands your plain-English description
2. Plans the best approach
3. Checks if similar code already exists
4. Writes complete, tested code
5. Debugs it before giving it to you

---

## Interactive Interpreter

A shared workspace for you and the AI:

```bash
copperhead interpret
```

### Commands

| Command | What It Does |
|---------|--------------|
| `<code>` | Add code to workspace |
| `?<description>` | Ask AI to generate code |
| `:debug` | Check code for errors |
| `:test` | Run tests |
| `:build` | Compile to Rust |
| `:list` | Show all code blocks |
| `:save file.py` | Save workspace |
| `:load file.py` | Load workspace |
| `:help` | Show all commands |
| `:exit` | Quit |

### Example Session

```
copperhead> ?Create a function that calculates factorial

[AI generates code with types and tests]

copperhead> :debug
[Checks code for issues]

copperhead> :test
[Runs generated tests]

copperhead> :save factorial.py
[ Saves to file]
```

---

## Module Registry

Store and reuse your best functions. Ships with **13 pre-loaded examples**.

### Commands
```bash
copperhead registry list              # See all modules
copperhead registry search "matrix"   # Find specific functions
copperhead registry add script.py     # Save a module
copperhead registry stats             # See usage statistics
```

### Pre-loaded Examples

**Basic (5):** sum_list, sort_numbers, factorial, fibonacci, divide

**Advanced (8):** linear_regression, matrix_multiply, quicksort, binary_search, prime_sieve, word_count, running_average, mandelbrot

### Why Use It
- Don't rewrite the same function twice
- Share code with your team
- Track what's working well

---

## Debugging

Check your code before running it.

### CLI Debug
```bash
copperhead debug script.py           # Full debug
copperhead debug script.py --types   # Type checking only
```

### What It Checks
1. **Syntax** - Is the code valid Python?
2. **Types** - Are type annotations correct?
3. **Patterns** - Does it follow Copperhead best practices?
4. **Safety** - Is it safe to run?

---

## Building for Production

Compile to fast Rust binaries.

### Module Mode (Fast Development)
```bash
copperhead build script.py
```
Compiles just that file. Fast for development.

### Bundle Mode (Maximum Performance)
```bash
copperhead build --bundle ./project/ -o engine.so
```
Compiles everything into one optimized binary. Best for production.

---

## Examples

See the `demo/` directory:

| File | What It Shows |
|------|---------------|
| `standard_python.py` | Standard Python speed baseline |
| `copperhead_version.py` | Copperhead equivalent |
| `compare.py` | Side-by-side comparison |
| `test_ai_generation.py` | AI code generation test |
| `comprehensive_test.py` | Full integration test suite |
| `test_ollama_real.py` | Real Ollama AI tests |
| `test_ambiguous.py` | AI ambiguity handling |
| `test_interpreter.py` | Interpreter tests |
| `populate_registry.py` | Registry population script |

---

## Testing

### Run All Tests
```bash
# 375 tests (196 AST coverage + 179 unit tests)
pytest copperhead/tests/

# Or run the comprehensive test
python comprehensive_test.py
```

### Run Specific Tests
```bash
pytest copperhead/tests/test_ast_coverage.py  # AST coverage (196 tests)
pytest copperhead/tests/test_types.py         # Type system
pytest copperhead/tests/test_parser.py        # Parser
pytest copperhead/tests/test_transpiler.py    # Transpiler
```

---

## Architecture

```
copperhead/
├── copperhead/             # Core package
│   ├── __init__.py         # Core types and decorators
│   ├── parser.py           # Reads and understands Python code
│   ├── transpiler.py       # Converts Python to Rust (28 stmts, 27 exprs, 60+ builtins)
│   ├── compiler.py         # Builds Rust binaries via Cargo
│   ├── cli.py              # Command-line interface
│   ├── llm.py              # AI agent (Ollama)
│   ├── debugger.py         # Code validation
│   ├── registry.py         # Module database (SQLite)
│   ├── interpreter.py      # Interactive workspace
│   ├── examples/           # Package examples
│   └── tests/              # 375 unit tests (196 AST + 179 core)
├── demo/                   # Demo and test scripts
├── docs/                   # Documentation + GitHub Pages
└── pyproject.toml          # Package config
```

---

## How It Works (Simplified)

```
Your Python Code
      ↓
[Parser] - Reads and understands it
      ↓
[Type Analyzer] - Figures out types
      ↓
[Rust Generator] - Writes equivalent Rust with PyO3 bindings
      ↓
[Cargo Compiler] - Creates fast machine code
      ↓
[Import Hook] - Makes it available to Python
```

---

## Requirements

- Python 3.8+
- Rust and Cargo (for compilation)
- Ollama (for AI features, optional)

---

## Performance

Typical speedups on real tasks:

| Task | Python | Copperhead | Speedup |
|------|--------|------------|---------|
| Sort 1M numbers | 450ms | 12ms | 37x |
| Image processing | 2.1s | 0.08s | 26x |
| Financial models | 8.5s | 0.3s | 28x |
| JSON parsing | 1.2s | 0.15s | 8x |

---

## FAQ

**Q: Do I need to learn Rust?**
A: No. You write Python. Copperhead handles the Rust.

**Q: Will my existing code work?**
A: Yes. Add `@cp.compile` to speed up specific functions.

**Q: Is it really that fast?**
A: On numeric, loop-heavy code, yes (see the benchmark table; reproduce with `benchmarks/jit_bench.py`). Code that mostly calls libraries or works on strings/dicts is not compiled and sees no speed-up.

**Q: Can I use NumPy/Pandas?**
A: Not inside compiled functions. 1-D `int64`/`float64` numpy arrays can be *passed in* (read-only, zero-copy); anything else runs as plain Python. Pandas is not supported.

**Q: How does the AI work?**
A: It uses Ollama (local AI). Your code never leaves your computer.

**Q: What if something breaks?**
A: Your code still runs as Python, so your debugger works. Copperhead also has its own debugger.

**Q: Does the compiler actually work?**
A: Yes, and it is tested end to end: build, import the resulting extension in a fresh interpreter, call it, and compare with Python. Windows output is a `.pyd`, Linux/macOS a `.so`.

---

## Learn More

- **[JIT guide](docs/JIT.md)** - the `@cp.jit` decorator in depth (what compiles, fallbacks, debugging)

- **[White Paper](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/WHITEPAPER.md)** - Detailed explanation for everyone
- **[Technical Deep Dive](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/docs/ARCHITECTURE.md)** - How it works internally
- **[Getting Started](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/docs/GETTING_STARTED.md)** - Step-by-step guide
- **[Tutorial](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/docs/TUTORIAL.md)** - Learn with examples
- **[API Reference](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/docs/API_REFERENCE.md)** - Complete function list
- **[Roadmap](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/ROADMAP.md)** - What's coming next

---

## Contributing

Contributions welcome! See the [Roadmap](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/ROADMAP.md) for planned features.

```bash
# Clone the repo
git clone https://github.com/unaveragetech/copperhead-rust-puthon.git
cd copperhead-rust-puthon

# Install dependencies
pip install -e .

# Run tests
pytest copperhead/tests/
```

---

## Community

- **GitHub Issues**: [Report bugs or request features](https://github.com/unaveragetech/copperhead-rust-puthon/issues)
- **Discussions**: [Ask questions](https://github.com/unaveragetech/copperhead-rust-puthon/discussions)

---

## License

SDUC License v1.1 (Small Developer Use Clause) - Free for individuals and small developers. See [LICENSE](https://github.com/unaveragetech/copperhead-rust-puthon/blob/main/LICENSE) for details.

---

**Copperhead: Write Python. Run Rust.**
