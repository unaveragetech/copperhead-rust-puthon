"""
Data processing example for Copperhead.
"""

import copperhead as cp


@cp.compile(target="rust")
def sum_array(data: list[cp.f64]) -> cp.f64:
    """Sum all elements in an array."""
    total: cp.f64 = 0.0
    for val in data:
        total += val
    return total


@cp.compile(target="rust")
def average_array(data: list[cp.f64]) -> cp.f64:
    """Calculate average of array elements."""
    total = sum_array(data)
    length = len(data)
    return total / length


@cp.compile(target="rust")
def max_array(data: list[cp.f64]) -> cp.f64:
    """Find maximum value in array."""
    if len(data) == 0:
        return 0.0
    
    max_val: cp.f64 = data[0]
    for val in data:
        if val > max_val:
            max_val = val
    return max_val


@cp.compile(target="rust")
def min_array(data: list[cp.f64]) -> cp.f64:
    """Find minimum value in array."""
    if len(data) == 0:
        return 0.0
    
    min_val: cp.f64 = data[0]
    for val in data:
        if val < min_val:
            min_val = val
    return min_val


@cp.compile(target="rust")
def filter_positive(data: list[cp.f64]) -> list[cp.f64]:
    """Filter array to keep only positive values."""
    result: list[cp.f64] = []
    for val in data:
        if val > 0.0:
            result.append(val)
    return result


@cp.compile(target="rust")
def map_square(data: list[cp.f64]) -> list[cp.f64]:
    """Map each element to its square."""
    result: list[cp.f64] = []
    for val in data:
        result.append(val * val)
    return result


@cp.compile(target="rust")
@cp.no_gil
def process_large_dataset(data: list[cp.f64]) -> cp.f64:
    """Process large dataset without GIL."""
    total: cp.f64 = 0.0
    for val in data:
        total += cp.math.sin(val) * cp.math.cos(val)
    return total


# Dictionary operations
@cp.compile(target="rust")
def count_frequencies(items: list[cp.str]) -> dict[cp.str, cp.i32]:
    """Count frequency of each item."""
    freq: dict[cp.str, cp.i32] = {}
    for item in items:
        if item in freq:
            freq[item] += 1
        else:
            freq[item] = 1
    return freq


# Tuple operations
@cp.compile(target="rust")
def swap_pair(pair: tuple[cp.f64, cp.f64]) -> tuple[cp.f64, cp.f64]:
    """Swap elements in a tuple."""
    return (pair[1], pair[0])


# Main function (runs as normal Python)
def main():
    """Main function demonstrating data processing."""
    print("Copperhead Data Processing Example")
    print("=" * 40)
    
    # Array operations
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    print(f"Data: {data}")
    print(f"Sum: {sum_array(data)}")
    print(f"Average: {average_array(data)}")
    print(f"Max: {max_array(data)}")
    print(f"Min: {min_array(data)}")
    
    # Filter and map
    mixed_data = [-2.0, -1.0, 0.0, 1.0, 2.0]
    print(f"\nMixed data: {mixed_data}")
    print(f"Positive values: {filter_positive(mixed_data)}")
    print(f"Squared values: {map_square(data)}")
    
    # Dictionary operations
    words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
    print(f"\nWords: {words}")
    print(f"Frequencies: {count_frequencies(words)}")
    
    # Tuple operations
    pair = (1.0, 2.0)
    print(f"\nOriginal pair: {pair}")
    print(f"Swapped pair: {swap_pair(pair)}")


if __name__ == "__main__":
    main()
