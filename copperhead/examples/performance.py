"""
Performance benchmark example for Copperhead.
"""

import copperhead as cp
import time
import math


@cp.compile(target="rust")
def fibonacci_rust(n: cp.i32) -> cp.i32:
    """Calculate fibonacci number in Rust."""
    if n <= 1:
        return n
    a: cp.i32 = 0
    b: cp.i32 = 1
    for _ in range(2, n + 1):
        temp = b
        b = a + b
        a = temp
    return b


def fibonacci_python(n: int) -> int:
    """Calculate fibonacci number in Python."""
    if n <= 1:
        return n
    a = 0
    b = 1
    for _ in range(2, n + 1):
        temp = b
        b = a + b
        a = temp
    return b


@cp.compile(target="rust")
def matrix_multiply_rust(a: list[list[cp.f64]], b: list[list[cp.f64]]) -> list[list[cp.f64]]:
    """Matrix multiplication in Rust."""
    rows_a = len(a)
    cols_a = len(a[0])
    cols_b = len(b[0])
    
    result: list[list[cp.f64]] = []
    for i in range(rows_a):
        row: list[cp.f64] = []
        for j in range(cols_b):
            sum_val: cp.f64 = 0.0
            for k in range(cols_a):
                sum_val += a[i][k] * b[k][j]
            row.append(sum_val)
        result.append(row)
    return result


def matrix_multiply_python(a: list, b: list) -> list:
    """Matrix multiplication in Python."""
    rows_a = len(a)
    cols_a = len(a[0])
    cols_b = len(b[0])
    
    result = []
    for i in range(rows_a):
        row = []
        for j in range(cols_b):
            sum_val = 0.0
            for k in range(cols_a):
                sum_val += a[i][k] * b[k][j]
            row.append(sum_val)
        result.append(row)
    return result


@cp.compile(target="rust")
@cp.no_gil
def compute_intensive_rust(n: cp.i32) -> cp.f64:
    """CPU intensive computation in Rust without GIL."""
    total: cp.f64 = 0.0
    for i in range(n):
        total += cp.math.sin(float(i)) * cp.math.cos(float(i))
    return total


def compute_intensive_python(n: int) -> float:
    """CPU intensive computation in Python."""
    total = 0.0
    for i in range(n):
        total += math.sin(float(i)) * math.cos(float(i))
    return total


def benchmark(name: str, rust_func, python_func, *args, iterations: int = 10):
    """Benchmark Rust vs Python functions."""
    print(f"\nBenchmarking: {name}")
    print("-" * 40)
    
    # Python benchmark
    start = time.time()
    for _ in range(iterations):
        python_result = python_func(*args)
    python_time = time.time() - start
    
    # Rust benchmark
    start = time.time()
    for _ in range(iterations):
        rust_result = rust_func(*args)
    rust_time = time.time() - start
    
    # Results
    speedup = python_time / rust_time if rust_time > 0 else float('inf')
    
    print(f"Python: {python_time:.4f}s")
    print(f"Rust:   {rust_time:.4f}s")
    print(f"Speedup: {speedup:.2f}x")
    
    return speedup


def main():
    """Main benchmark function."""
    print("Copperhead Performance Benchmark")
    print("=" * 50)
    
    # Fibonacci benchmark
    n = 30
    benchmark(
        f"Fibonacci({n})",
        fibonacci_rust,
        fibonacci_python,
        n,
        iterations=100
    )
    
    # Matrix multiplication benchmark
    size = 50
    a = [[float(i + j) for j in range(size)] for i in range(size)]
    b = [[float(i * j) for j in range(size)] for i in range(size)]
    
    benchmark(
        f"Matrix Multiplication ({size}x{size})",
        matrix_multiply_rust,
        matrix_multiply_python,
        a, b,
        iterations=5
    )
    
    # CPU intensive benchmark
    n = 100000
    benchmark(
        f"CPU Intensive ({n} iterations)",
        compute_intensive_rust,
        compute_intensive_python,
        n,
        iterations=10
    )
    
    print("\n" + "=" * 50)
    print("Benchmark complete!")


if __name__ == "__main__":
    main()
