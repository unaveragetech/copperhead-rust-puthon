"""
Abstract examples demonstrating advanced Copperhead features.
These examples test complex patterns and edge cases.
"""

import copperhead as cp
from typing import Optional


# ============================================================
# Example 1: Generic Data Structure with Ownership
# ============================================================

class Node:
    """Generic tree node."""
    def __init__(self, value: float, children: list = None):
        self.value = value
        self.children = children or []


@cp.compile(target="rust")
def tree_sum(root: cp.ref[Node]) -> cp.f64:
    """Calculate sum of all nodes in a tree (immutable borrow)."""
    total: cp.f64 = root.value
    for child in root.children:
        total += tree_sum(child)
    return total


@cp.compile(target="rust")
@cp.no_gil
def tree_map(root: cp.mut[Node], f: cp.ref[callable]) -> None:
    """Apply function to all nodes in tree (mutable borrow)."""
    root.value = f(root.value)
    for child in root.children:
        tree_map(child, f)


# ============================================================
# Example 2: Complex Type System Usage
# ============================================================

@cp.compile(target="rust")
def matrix_multiply(
    a: list[list[cp.f64]], 
    b: list[list[cp.f64]]
) -> list[list[cp.f64]]:
    """Matrix multiplication with full type safety."""
    rows_a: cp.i32 = len(a)
    cols_a: cp.i32 = len(a[0])
    cols_b: cp.i32 = len(b[0])
    
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


@cp.compile(target="rust")
def transpose(matrix: list[list[cp.f64]]) -> list[list[cp.f64]]:
    """Transpose a matrix."""
    if not matrix:
        return []
    
    rows: cp.i32 = len(matrix)
    cols: cp.i32 = len(matrix[0])
    
    result: list[list[cp.f64]] = []
    for j in range(cols):
        row: list[cp.f64] = []
        for i in range(rows):
            row.append(matrix[i][j])
        result.append(row)
    
    return result


# ============================================================
# Example 3: Error Handling Patterns
# ============================================================

@cp.compile(target="rust")
def safe_divide(a: cp.f64, b: cp.f64):
    """Safe division with error handling."""
    if b == 0.0:
        return cp.Err("Division by zero")
    return cp.Ok(a / b)


@cp.compile(target="rust")
def safe_index(lst: list, index: int):
    """Safe list indexing with bounds checking."""
    if index < 0 or index >= len(lst):
        return cp.Err(f"Index {index} out of bounds")
    return cp.Ok(lst[index])


@cp.compile(target="rust")
def chain_operations(x: cp.f64):
    """Chain multiple operations with error handling."""
    if x < 0.0:
        return cp.Err("Cannot take square root of negative number")
    sqrt_val = cp.math.sqrt(x)
    result = safe_divide(sqrt_val, 2.0)
    if result.is_err():
        return result
    val = result.unwrap()
    if val <= 0.0:
        return cp.Err("Cannot take logarithm of non-positive number")
    return cp.Ok(cp.math.log(val))


# ============================================================
# Example 4: Advanced Collection Operations
# ============================================================

@cp.compile(target="rust")
@cp.no_gil
def quicksort(arr: list[cp.f64]) -> list[cp.f64]:
    """Quicksort implementation."""
    if len(arr) <= 1:
        return arr
    
    pivot: cp.f64 = arr[len(arr) // 2]
    left: list[cp.f64] = []
    middle: list[cp.f64] = []
    right: list[cp.f64] = []
    
    for x in arr:
        if x < pivot:
            left.append(x)
        elif x > pivot:
            right.append(x)
        else:
            middle.append(x)
    
    return quicksort(left) + middle + quicksort(right)


@cp.compile(target="rust")
def merge_sorted(a: list[cp.f64], b: list[cp.f64]) -> list[cp.f64]:
    """Merge two sorted lists."""
    result: list[cp.f64] = []
    i: cp.i32 = 0
    j: cp.i32 = 0
    
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    
    while i < len(a):
        result.append(a[i])
        i += 1
    
    while j < len(b):
        result.append(b[j])
        j += 1
    
    return result


@cp.compile(target="rust")
def unique_elements(lst: list[cp.f64]) -> list[cp.f64]:
    """Get unique elements while preserving order."""
    seen: set[cp.f64] = set()
    result: list[cp.f64] = []
    
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    
    return result


# ============================================================
# Example 5: Functional Programming Patterns
# ============================================================

@cp.compile(target="rust")
def map_list(lst: list[cp.f64], f: cp.ref[callable]) -> list[cp.f64]:
    """Apply function to each element."""
    result: list[cp.f64] = []
    for item in lst:
        result.append(f(item))
    return result


@cp.compile(target="rust")
def filter_list(lst: list[cp.f64], predicate: cp.ref[callable]) -> list[cp.f64]:
    """Filter list by predicate."""
    result: list[cp.f64] = []
    for item in lst:
        if predicate(item):
            result.append(item)
    return result


@cp.compile(target="rust")
def reduce_list(lst: list[cp.f64], f: cp.ref[callable], initial: cp.f64) -> cp.f64:
    """Reduce list to single value."""
    acc: cp.f64 = initial
    for item in lst:
        acc = f(acc, item)
    return acc


# ============================================================
# Example 6: State Machine Pattern
# ============================================================

class StateMachine:
    """Simple state machine."""
    def __init__(self):
        self.state = "idle"
        self.data = {}
        self.history = []


@cp.compile(target="rust")
def transition(
    sm, 
    action: str, 
    payload
):
    """Process state transition."""
    old_state = sm.state
    
    if sm.state == "idle":
        if action == "start":
            sm.state = "running"
            sm.data = payload
        else:
            return cp.Err(f"Invalid action '{action}' in idle state")
    
    elif sm.state == "running":
        if action == "complete":
            sm.state = "done"
        elif action == "fail":
            sm.state = "error"
        else:
            return cp.Err(f"Invalid action '{action}' in running state")
    
    elif sm.state == "done" or sm.state == "error":
        if action == "reset":
            sm.state = "idle"
            sm.data = {}
        else:
            return cp.Err(f"Invalid action '{action}' in terminal state")
    
    sm.history.append(f"{old_state} -> {sm.state} ({action})")
    return cp.Ok(sm.state)


# ============================================================
# Example 7: Numerical Algorithms
# ============================================================

@cp.compile(target="rust")
@cp.no_gil
def numerical_derivative(
    f: cp.ref[callable], 
    x: cp.f64, 
    h: cp.f64 = 1e-7
) -> cp.f64:
    """Numerical derivative using central difference."""
    return (f(x + h) - f(x - h)) / (2.0 * h)


@cp.compile(target="rust")
@cp.no_gil
def newton_raphson(
    f,
    f_prime,
    x0: float,
    tolerance: float = 1e-10,
    max_iterations: int = 100
):
    """Newton-Raphson root finding."""
    x = x0
    
    for i in range(max_iterations):
        fx = f(x)
        
        if cp.math.abs(fx) < tolerance:
            return cp.Ok(x)
        
        fpx = f_prime(x)
        if fpx == 0.0:
            return cp.Err("Derivative is zero, cannot continue")
        
        x = x - fx / fpx
    
    return cp.Err("Failed to converge")


@cp.compile(target="rust")
@cp.no_gil
def monte_carlo_pi(n_samples: cp.i32) -> cp.f64:
    """Estimate PI using Monte Carlo method."""
    import random
    
    inside_circle: cp.i32 = 0
    
    for _ in range(n_samples):
        x: cp.f64 = random.random() * 2.0 - 1.0
        y: cp.f64 = random.random() * 2.0 - 1.0
        
        if x * x + y * y <= 1.0:
            inside_circle += 1
    
    return 4.0 * inside_circle / n_samples


# ============================================================
# Example 8: String Processing (with PyO3 fallback)
# ============================================================

@cp.compile(target="rust")
def count_words(text: cp.str) -> dict[cp.str, cp.i32]:
    """Count word frequencies."""
    words: list[cp.str] = text.lower().split()
    freq: dict[cp.str, cp.i32] = {}
    
    for word in words:
        if word in freq:
            freq[word] += 1
        else:
            freq[word] = 1
    
    return freq


@cp.compile(target="rust")
def char_frequency(text: cp.str) -> dict[cp.str, cp.i32]:
    """Count character frequencies."""
    freq: dict[cp.str, cp.i32] = {}
    
    for char in text:
        if char in freq:
            freq[char] += 1
        else:
            freq[char] = 1
    
    return freq


# ============================================================
# Example 9: Graph Algorithms
# ============================================================

class Graph:
    """Adjacency list graph representation."""
    def __init__(self):
        self.adjacency: dict[str, list[str]] = {}


@cp.compile(target="rust")
def bfs(graph: cp.ref[Graph], start: cp.str) -> list[cp.str]:
    """Breadth-first search."""
    visited: set[cp.str] = set()
    queue: list[cp.str] = [start]
    result: list[cp.str] = []
    
    while len(queue) > 0:
        node: cp.str = queue[0]
        queue = queue[1:]
        
        if node in visited:
            continue
        
        visited.add(node)
        result.append(node)
        
        if node in graph.adjacency:
            for neighbor in graph.adjacency[node]:
                if neighbor not in visited:
                    queue.append(neighbor)
    
    return result


@cp.compile(target="rust")
def has_cycle(graph: cp.ref[Graph]) -> cp.bool:
    """Check if graph has a cycle (DFS approach)."""
    visited: set[cp.str] = set()
    recursion_stack: set[cp.str] = set()
    
    def dfs(node: cp.str) -> cp.bool:
        visited.add(node)
        recursion_stack.add(node)
        
        if node in graph.adjacency:
            for neighbor in graph.adjacency[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True
        
        recursion_stack.remove(node)
        return False
    
    for node in graph.adjacency:
        if node not in visited:
            if dfs(node):
                return True
    
    return False


# ============================================================
# Example 10: Performance-Critical Code
# ============================================================

@cp.compile(target="rust")
@cp.no_gil
def fft_radix2(signal: list[cp.f64]) -> list[cp.f64]:
    """Simple radix-2 FFT (simplified version)."""
    n: cp.i32 = len(signal)
    
    if n <= 1:
        return signal
    
    if n % 2 != 0:
        # Pad to next power of 2
        return signal
    
    even: list[cp.f64] = signal[0::2]
    odd: list[cp.f64] = signal[1::2]
    
    even_fft: list[cp.f64] = fft_radix2(even)
    odd_fft: list[cp.f64] = fft_radix2(odd)
    
    result: list[cp.f64] = [0.0] * n
    for k in range(n // 2):
        t: cp.f64 = cp.math.cos(2.0 * 3.141592653589793 * k / n) * odd_fft[k]
        result[k] = even_fft[k] + t
        result[k + n // 2] = even_fft[k] - t
    
    return result


@cp.compile(target="rust")
@cp.no_gil
def convolve1d(signal: list[cp.f64], kernel: list[cp.f64]) -> list[cp.f64]:
    """1D convolution."""
    n: cp.i32 = len(signal)
    k: cp.i32 = len(kernel)
    result: list[cp.f64] = [0.0] * n
    
    for i in range(n):
        for j in range(k):
            if i - j >= 0:
                result[i] += signal[i - j] * kernel[j]
    
    return result


# ============================================================
# Main function for testing
# ============================================================

def main():
    """Test the abstract examples."""
    print("Testing abstract Copperhead examples...")
    
    # Test matrix operations
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    print(f"Matrix multiply: {matrix_multiply(a, b)}")
    print(f"Transpose: {transpose(a)}")
    
    # Test error handling
    print(f"Safe divide: {safe_divide(10.0, 3.0)}")
    print(f"Safe divide by zero: {safe_divide(10.0, 0.0)}")
    print(f"Chain operations: {chain_operations(100.0)}")
    
    # Test sorting
    import random
    arr = [random.random() * 100 for _ in range(10)]
    print(f"Quicksort: {quicksort(arr)}")
    
    print("All tests passed!")


if __name__ == "__main__":
    main()
