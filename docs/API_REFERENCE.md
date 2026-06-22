# Copperhead API Reference

Complete reference for all Copperhead functions, types, and modules.

---

## Core Decorators

### `@cp.compile(target="rust")`

Marks a function for Rust compilation.

```python
@cp.compile(target="rust")
def my_function(x: cp.f64) -> cp.f64:
    return x * 2
```

**Parameters:**
- `target` (str): Compilation target. Default: `"rust"`

---

### `@cp.no_gil`

Releases the GIL for true parallel execution.

```python
@cp.compile(target="rust")
@cp.no_gil
def cpu_heavy(n: int) -> float:
    total = 0.0
    for i in range(n):
        total += cp.math.sin(float(i))
    return total
```

---

## Type System

### Primitive Types

| Type | Python Equivalent | Rust Type | Size |
|------|-------------------|-----------|------|
| `cp.i8` | `int` | `i8` | 1 byte |
| `cp.i16` | `int` | `i16` | 2 bytes |
| `cp.i32` | `int` | `i32` | 4 bytes |
| `cp.i64` | `int` | `i64` | 8 bytes |
| `cp.u8` | `int` | `u8` | 1 byte |
| `cp.u16` | `int` | `u16` | 2 bytes |
| `cp.u32` | `int` | `u32` | 4 bytes |
| `cp.u64` | `int` | `u64` | 8 bytes |
| `cp.usize` | `int` | `usize` | Platform |
| `cp.isize` | `int` | `isize` | Platform |
| `cp.f32` | `float` | `f32` | 4 bytes |
| `cp.f64` | `float` | `f64` | 8 bytes |
| `cp.bool` | `bool` | `bool` | 1 byte |
| `cp.str` | `str` | `String` | Heap |
| `cp.bytes` | `bytes` | `Vec<u8>` | Heap |
| `cp.char` | `chr` | `char` | 4 bytes |

### Collection Types

| Copperhead | Python | Rust |
|------------|--------|------|
| `Vec[T]` | `list[T]` | `Vec<T>` |
| `HashMap[K,V]` | `dict[K,V]` | `HashMap<K,V>` |
| `Option[T]` | `Optional[T]` | `Option<T>` |
| `Result[T,E]` | `Union[T, E]` | `Result<T,E>` |

### Ownership Types

| Type | Purpose | Example |
|------|---------|---------|
| `cp.mut[T]` | Mutable reference | `state: cp.mut[MyClass]` |
| `cp.ref[T]` | Immutable reference | `data: cp.ref[MyClass]` |

---

## Collections

### Vec[T]

Dynamic array implementation.

```python
# Create
numbers = cp.Vec([1, 2, 3, 4, 5])
empty = cp.Vec()

# Methods
numbers.append(6)           # Add element
numbers.extend([7, 8])     # Add multiple
numbers.pop()               # Remove last
numbers.remove(3)           # Remove by value
numbers.contains(4)         # Check existence
numbers.len()               # Get length
numbers.is_empty()          # Check if empty
numbers.clear()             # Remove all
numbers[index]              # Access by index
numbers[1:3]                # Slice
```

### HashMap[K,V]

Hash map implementation.

```python
# Create
data = cp.HashMap({"name": "Alice", "age": "30"})

# Methods
data.set("city", "NYC")     # Add/update
data.get("name")            # Get value
data.remove("age")          # Remove key
data.contains_key("name")   # Check key
data.keys()                 # Get all keys
data.values()               # Get all values
data.items()                # Get all pairs
data.len()                  # Get length
data.is_empty()             # Check if empty
data.clear()                # Remove all
```

### Option[T]

Optional value container.

```python
# Create
some_value = cp.Some(42)
no_value = cp.None_

# Methods
some_value.is_some()        # Check if has value
some_value.is_none()        # Check if empty
some_value.unwrap()         # Get value (panics if None)
some_value.unwrap_or(0)     # Get value or default
some_value.map(lambda x: x * 2)  # Transform
```

### Result[T,E]

Error handling container.

```python
# Create
success = cp.Ok(42)
failure = cp.Err("Something went wrong")

# Methods
success.is_ok()             # Check if success
success.is_err()            # Check if error
success.unwrap()            # Get value (panics if Err)
success.unwrap_or(0)        # Get value or default
success.map(lambda x: x * 2)  # Transform success
```

---

## Math Module

### Basic Operations

```python
cp.math.sin(x)          # Sine
cp.math.cos(x)          # Cosine
cp.math.tan(x)          # Tangent
cp.math.asin(x)         # Arc sine
cp.math.acos(x)         # Arc cosine
cp.math.atan(x)         # Arc tangent
```

### Power and Root

```python
cp.math.sqrt(x)         # Square root
cp.math.cbrt(x)         # Cube root
cp.math.pow(x, y)       # Power (x^y)
cp.math.exp(x)          # e^x
cp.math.log(x)          # Natural log
cp.math.log2(x)         # Log base 2
cp.math.log10(x)        # Log base 10
```

### Rounding

```python
cp.math.floor(x)        # Round down
cp.math.ceil(x)         # Round up
cp.math.round(x)        # Round to nearest
```

### Comparison

```python
cp.math.abs(x)          # Absolute value
cp.math.min(a, b)       # Minimum
cp.math.max(a, b)       # Maximum
```

### Constants

```python
cp.math.PI              # 3.14159...
cp.math.E               # 2.71828...
cp.math.TAU             # 6.28318...
cp.math.INFINITY        # Infinity
cp.math.NAN             # Not a Number
```

---

## CLI Commands

### Build

```bash
copperhead build <file.py>              # Build single file
copperhead build <file.py> -o out.so    # Specify output
copperhead build --bundle ./src/        # Bundle all files
copperhead build --clean                # Clean cache first
```

### Lint

```bash
copperhead lint <file.py>               # Check for issues
copperhead lint <file.py> --fix         # Auto-fix issues
```

### Transpile

```bash
copperhead transpile <file.py>          # Generate Rust code
copperhead transpile <file.py> -o out.rs # Specify output
```

### Check

```bash
copperhead check <file.py>              # Type check only
```

### Cache

```bash
copperhead cache list                   # Show cached files
copperhead cache clear                  # Clear all cache
copperhead cache clear <file.py>        # Clear specific cache
```

### Generate

```bash
copperhead generate "description"       # Generate from English
copperhead generate "description" -o out.py # Specify output
```

### Interactive

```bash
copperhead interactive                  # Start session
copperhead interactive --model model    # Use specific model
```

### Debug

```bash
copperhead debug <file.py>              # Full debug
copperhead debug <file.py> --types      # Type check only
copperhead debug <file.py> --syntax     # Syntax check only
```

### Registry

```bash
copperhead registry list                # List all modules
copperhead registry search "query"      # Search modules
copperhead registry add <file.py>       # Add to registry
copperhead registry stats               # Show statistics
```

### Interpret

```bash
copperhead interpret                    # Start interpreter
copperhead interpret --load file.py     # Load workspace
```

---

## Interpreter Commands

| Command | Description |
|---------|-------------|
| `<code>` | Add code block |
| `?<description>` | Generate code with AI |
| `:debug` | Debug all code |
| `:test` | Run tests |
| `:build` | Compile to Rust |
| `:list` | Show all blocks |
| `:save <file>` | Save workspace |
| `:load <file>` | Load workspace |
| `:help` | Show help |
| `:exit` | Quit |

---

## Error Handling

### CopperheadError

Base exception for all Copperhead errors.

```python
try:
    result = process(data)
except cp.CopperheadError as e:
    print(f"Error: {e}")
```

### CompilationError

Raised when compilation fails.

```python
try:
    cp.compile_module("bad_code.py")
except cp.CompilationError as e:
    print(f"Compilation failed: {e}")
```

### TranspilationError

Raised when transpilation fails.

```python
try:
    cp.transpile("bad_code.py")
except cp.TranspilationError as e:
    print(f"Transpilation failed: {e}")
```

---

## Configuration

### copperhead.toml

```toml
[compiler]
target = "rust"
optimization = "release"  # "debug" or "release"
cache_dir = ".copperhead"

[llm]
model = "qwen2.5-coder"
temperature = 0.7
max_tokens = 2048

[registry]
db_path = "copperhead_registry.db"

[debugger]
syntax_check = true
type_check = true
pattern_check = true
safety_check = true
```

---

## Examples

### Basic Usage

```python
import copperhead as cp

@cp.compile(target="rust")
def add(a: cp.f64, b: cp.f64) -> cp.f64:
    return a + b

result = add(2.0, 3.0)  # Runs at Rust speed
```

### Collections

```python
@cp.compile(target="rust")
def sum_list(numbers: list[cp.f64]) -> cp.f64:
    total = 0.0
    for n in numbers:
        total += n
    return total
```

### Error Handling

```python
@cp.compile(target="rust")
def divide(a: cp.f64, b: cp.f64):
    if b == 0.0:
        return cp.Err("Cannot divide by zero")
    return cp.Ok(a / b)
```

### Ownership

```python
@cp.compile(target="rust")
def update_state(state: cp.mut[MyClass]) -> None:
    state.value += 1

@cp.compile(target="rust")
def read_data(data: cp.ref[MyClass]) -> cp.f64:
    return data.value
```

---

## Type Conversion

### Python to Rust

| Python | Rust | Notes |
|--------|------|-------|
| `int` | `i64` | Default integer |
| `float` | `f64` | Default float |
| `bool` | `bool` | |
| `str` | `String` | |
| `list` | `Vec<PyObject>` | Dynamic |
| `dict` | `HashMap<PyObject, PyObject>` | Dynamic |

### Explicit Conversion

```python
# Use cp types for explicit conversion
x: cp.i32 = 42      # Force i32
y: cp.f32 = 3.14    # Force f32
z: cp.u8 = 255      # Force u8
```
