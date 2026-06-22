# Copperhead Tutorial

Learn Copperhead step-by-step with practical examples.

---

## Lesson 1: The Basics

### What You'll Learn
- How to mark functions for Rust compilation
- How to add types for speed
- How to run your code

### Your First Function

Create `lesson1.py`:

```python
import copperhead as cp

@cp.compile(target="rust")
def square(x: cp.f64) -> cp.f64:
    """Calculate the square of a number."""
    return x * x

# Test it
if __name__ == "__main__":
    print(f"square(5) = {square(5.0)}")
    print(f"square(10) = {square(10.0)}")
    print(f"square(100) = {square(100.0)}")
```

Run it:
```bash
python lesson1.py
```

Output:
```
square(5) = 25.0
square(10) = 100.0
square(100) = 10000.0
```

### Key Points
1. `@cp.compile(target="rust")` marks the function for Rust compilation
2. Type annotations (`cp.f64`) tell Copperhead what types to use
3. The function runs as normal Python until compiled

---

## Lesson 2: Working with Collections

### Lists

Create `lesson2.py`:

```python
import copperhead as cp

@cp.compile(target="rust")
def find_max(numbers: list[cp.f64]) -> cp.f64:
    """Find the maximum value in a list."""
    if len(numbers) == 0:
        return 0.0
    
    max_val = numbers[0]
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

@cp.compile(target="rust")
def filter_positive(numbers: list[cp.f64]) -> list[cp.f64]:
    """Keep only positive numbers."""
    result = cp.Vec()
    for n in numbers:
        if n > 0.0:
            result.append(n)
    return result

# Test it
if __name__ == "__main__":
    data = [3.0, -1.0, 4.0, -5.0, 2.0, 9.0, -7.0]
    
    print(f"Data: {data}")
    print(f"Max: {find_max(data)}")
    print(f"Positive: {filter_positive(data)}")
```

Run it:
```bash
python lesson2.py
```

Output:
```
Data: [3.0, -1.0, 4.0, -5.0, 2.0, 9.0, -7.0]
Max: 9.0
Positive: [3.0, 4.0, 2.0, 9.0]
```

### Dictionaries

```python
@cp.compile(target="rust")
def word_count(text: str) -> dict:
    """Count occurrences of each word."""
    words = cp.HashMap()
    for word in text.split():
        if words.contains_key(word):
            words.set(word, words.get(word) + 1)
        else:
            words.set(word, 1)
    return words

# Test it
text = "the quick brown fox jumps over the lazy dog the fox"
counts = word_count(text)
print(f"Word counts: {counts}")
```

---

## Lesson 3: Error Handling

### Using Result Type

Create `lesson3.py`:

```python
import copperhead as cp

@cp.compile(target="rust")
def safe_divide(a: cp.f64, b: cp.f64):
    """Divide two numbers safely."""
    if b == 0.0:
        return cp.Err("Division by zero")
    return cp.Ok(a / b)

@cp.compile(target="rust")
def safe_sqrt(x: cp.f64):
    """Calculate square root safely."""
    if x < 0.0:
        return cp.Err("Cannot take square root of negative number")
    return cp.Ok(cp.math.sqrt(x))

# Test it
if __name__ == "__main__":
    # Test division
    result1 = safe_divide(10.0, 2.0)
    result2 = safe_divide(10.0, 0.0)
    
    print(f"10 / 2 = {result1.unwrap() if result1.is_ok() else result1.unwrap_err()}")
    print(f"10 / 0 = {result2.unwrap() if result2.is_ok() else result2.unwrap_err()}")
    
    # Test square root
    result3 = safe_sqrt(16.0)
    result4 = safe_sqrt(-4.0)
    
    print(f"sqrt(16) = {result3.unwrap() if result3.is_ok() else result3.unwrap_err()}")
    print(f"sqrt(-4) = {result4.unwrap() if result4.is_ok() else result4.unwrap_err()}")
```

Run it:
```bash
python lesson3.py
```

Output:
```
10 / 2 = 5.0
10 / 0 = Division by zero
sqrt(16) = 4.0
sqrt(-4) = Cannot take square root of negative number
```

---

## Lesson 4: Math Operations

### Using the Math Module

Create `lesson4.py`:

```python
import copperhead as cp

@cp.compile(target="rust")
def circle_stats(radius: cp.f64) -> dict:
    """Calculate circle statistics."""
    area = cp.math.PI * radius * radius
    circumference = 2.0 * cp.math.PI * radius
    return {"area": area, "circumference": circumference}

@cp.compile(target="rust")
def statistics(numbers: list[cp.f64]) -> dict:
    """Calculate basic statistics."""
    n = len(numbers)
    if n == 0:
        return {"mean": 0.0, "std": 0.0}
    
    # Calculate mean
    total = 0.0
    for x in numbers:
        total += x
    mean = total / n
    
    # Calculate standard deviation
    sum_sq = 0.0
    for x in numbers:
        diff = x - mean
        sum_sq += diff * diff
    std = cp.math.sqrt(sum_sq / n)
    
    return {"mean": mean, "std": std}

# Test it
if __name__ == "__main__":
    # Circle
    stats = circle_stats(5.0)
    print(f"Circle (r=5): area={stats['area']:.2f}, circumference={stats['circumference']:.2f}")
    
    # Statistics
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    result = statistics(data)
    print(f"Data: {data}")
    print(f"Mean: {result['mean']:.2f}")
    print(f"Std Dev: {result['std']:.2f}")
```

---

## Lesson 5: Ownership

### Understanding Mutable vs Immutable References

Create `lesson5.py`:

```python
import copperhead as cp

@cp.datatype
class Counter:
    value: cp.i64

@cp.compile(target="rust")
def increment(counter: cp.mut[Counter]) -> None:
    """Increment counter (mutable reference)."""
    counter.value += 1

@cp.compile(target="rust")
def get_value(counter: cp.ref[Counter]) -> cp.i64:
    """Get counter value (immutable reference)."""
    return counter.value

# Test it
if __name__ == "__main__":
    counter = Counter(value=0)
    
    print(f"Initial: {get_value(counter)}")
    
    for i in range(5):
        increment(counter)
        print(f"After increment {i+1}: {get_value(counter)}")
```

Run it:
```bash
python lesson5.py
```

Output:
```
Initial: 0
After increment 1: 1
After increment 2: 2
After increment 3: 3
After increment 4: 4
After increment 5: 5
```

### Why Ownership Matters

- **Immutable references** (`cp.ref[T]`): Multiple readers allowed, no writers
- **Mutable references** (`cp.mut[T]`): Only one writer allowed, no readers
- This prevents data races in concurrent code

---

## Lesson 6: GIL Release

### True Parallel Processing

Create `lesson6.py`:

```python
import copperhead as cp
import time

@cp.compile(target="rust")
@cp.no_gil
def cpu_heavy(n: cp.i64) -> cp.f64:
    """CPU-intensive calculation."""
    total = 0.0
    for i in range(n):
        total += cp.math.sin(float(i))
    return total

# Test it
if __name__ == "__main__":
    n = 10_000_000
    
    start = time.time()
    result = cpu_heavy(n)
    elapsed = time.time() - start
    
    print(f"Calculated {n} sine values")
    print(f"Result: {result:.6f}")
    print(f"Time: {elapsed:.3f} seconds")
```

Run it:
```bash
python lesson6.py
```

The `@cp.no_gil` decorator releases the GIL, allowing true parallel execution.

---

## Lesson 7: Building a Complete Application

### Data Processor

Create `lesson7.py`:

```python
import copperhead as cp

@cp.datatype
class DataPoint:
    x: cp.f64
    y: cp.f64

@cp.compile(target="rust")
def linear_regression(points: list[DataPoint]) -> dict:
    """Calculate linear regression."""
    n = len(points)
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0}
    
    # Calculate means
    sum_x = 0.0
    sum_y = 0.0
    for p in points:
        sum_x += p.x
        sum_y += p.y
    mean_x = sum_x / n
    mean_y = sum_y / n
    
    # Calculate slope and intercept
    sum_xy = 0.0
    sum_x2 = 0.0
    for p in points:
        diff_x = p.x - mean_x
        diff_y = p.y - mean_y
        sum_xy += diff_x * diff_y
        sum_x2 += diff_x * diff_x
    
    if sum_x2 == 0.0:
        return {"slope": 0.0, "intercept": mean_y, "r_squared": 0.0}
    
    slope = sum_xy / sum_x2
    intercept = mean_y - slope * mean_x
    
    # Calculate R-squared
    ss_res = 0.0
    ss_tot = 0.0
    for p in points:
        predicted = slope * p.x + intercept
        ss_res += (p.y - predicted) ** 2
        ss_tot += (p.y - mean_y) ** 2
    
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0.0 else 0.0
    
    return {"slope": slope, "intercept": intercept, "r_squared": r_squared}

@cp.compile(target="rust")
def predict(x: cp.f64, slope: cp.f64, intercept: cp.f64) -> cp.f64:
    """Predict y value from x."""
    return slope * x + intercept

# Test it
if __name__ == "__main__":
    # Create sample data
    points = [
        DataPoint(1.0, 2.0),
        DataPoint(2.0, 4.0),
        DataPoint(3.0, 5.0),
        DataPoint(4.0, 4.0),
        DataPoint(5.0, 5.0),
    ]
    
    # Calculate regression
    result = linear_regression(points)
    
    print("Linear Regression Results:")
    print(f"  Slope: {result['slope']:.4f}")
    print(f"  Intercept: {result['intercept']:.4f}")
    print(f"  R-squared: {result['r_squared']:.4f}")
    
    # Make predictions
    print("\nPredictions:")
    for x in [1.0, 2.5, 4.0, 6.0]:
        y = predict(x, result['slope'], result['intercept'])
        print(f"  x={x:.1f} -> y={y:.2f}")
```

---

## Lesson 8: Using the AI Agent

### Generate Code

```bash
copperhead generate "Create a function that sorts a list using merge sort"
```

### Interactive Session

```bash
copperhead interactive
```

```
copperhead> ?Create a function that finds all prime numbers up to n

[AI generates code]

copperhead> :debug

[Checks code for issues]

copperhead> :test

[Runs tests]

copperhead> :save primes.py

[ Saves to file]
```

---

## Lesson 9: Module Registry

### Store Your Best Code

```bash
copperhead registry add lesson7.py
```

### Search Later

```bash
copperhead registry search "linear regression"
```

### Use Existing Code

```python
# The AI checks the registry first
copperhead generate "Create a linear regression function"
# Uses existing code if available
```

---

## Lesson 10: Production Build

### Compile for Speed

```bash
copperhead build lesson7.py
```

### Bundle Entire Project

```bash
copperhead build --bundle ./src/ -o engine.so
```

### Use in Production

```python
import lesson7  # Now runs at Rust speed!
```

---

## Next Steps

1. **Try the examples** in `examples/`
2. **Read the API reference** for all functions
3. **Build your own projects** with Copperhead
4. **Share your code** in the registry

---

## Summary

| Lesson | What You Learned |
|--------|------------------|
| 1 | Basic compilation |
| 2 | Collections (Vec, HashMap) |
| 3 | Error handling (Result) |
| 4 | Math operations |
| 5 | Ownership (mut/ref) |
| 6 | GIL release for threading |
| 7 | Complete application |
| 8 | AI agent |
| 9 | Module registry |
| 10 | Production build |

**You now know Copperhead!**
