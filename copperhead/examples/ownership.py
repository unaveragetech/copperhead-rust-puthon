"""
Ownership and borrowing example for Copperhead.
"""

import copperhead as cp


# State class for demonstration
class State:
    def __init__(self):
        self.counter = 0
        self.data = []


# Data class for demonstration
class Data:
    def __init__(self, values):
        self.values = values


@cp.compile(target="rust")
def mutate_state(state: cp.mut[State], value: cp.f64) -> None:
    """Mutably borrow state to modify it."""
    state.counter += 1
    state.data.append(value)


@cp.compile(target="rust")
def read_data(ref_data: cp.ref[Data]) -> cp.f64:
    """Immutably borrow data to read it."""
    total: cp.f64 = 0.0
    for val in ref_data.values:
        total += val
    return total


# Example with mutable references
@cp.compile(target="rust")
def increment_all(data: cp.mut[list[cp.f64]], amount: cp.f64) -> None:
    """Increment all values in a list."""
    for i in range(len(data)):
        data[i] += amount


@cp.compile(target="rust")
def get_statistics(ref_data: cp.ref[list[cp.f64]]) -> tuple[cp.f64, cp.f64, cp.f64]:
    """Get statistics from data without modifying it."""
    if len(ref_data) == 0:
        return (0.0, 0.0, 0.0)
    
    total: cp.f64 = 0.0
    min_val: cp.f64 = ref_data[0]
    max_val: cp.f64 = ref_data[0]
    
    for val in ref_data:
        total += val
        if val < min_val:
            min_val = val
        if val > max_val:
            max_val = val
    
    avg = total / len(ref_data)
    return (avg, min_val, max_val)


# Main function
def main():
    """Main function demonstrating ownership."""
    print("Copperhead Ownership Example")
    print("=" * 40)
    
    # Mutable state
    state = State()
    print(f"Initial state: counter={state.counter}, data={state.data}")
    
    mutate_state(state, 1.0)
    print(f"After mutate_state(state, 1.0): counter={state.counter}, data={state.data}")
    
    mutate_state(state, 2.0)
    print(f"After mutate_state(state, 2.0): counter={state.counter}, data={state.data}")
    
    # Immutable data
    data = Data([1.0, 2.0, 3.0, 4.0, 5.0])
    total = read_data(data)
    print(f"\nData values: {data.values}")
    print(f"Total from read_data: {total}")
    
    # Mutable list
    numbers = [1.0, 2.0, 3.0, 4.0, 5.0]
    print(f"\nOriginal numbers: {numbers}")
    
    increment_all(numbers, 10.0)
    print(f"After increment_all(numbers, 10.0): {numbers}")
    
    # Immutable statistics
    stats_data = [10.0, 20.0, 30.0, 40.0, 50.0]
    avg, min_val, max_val = get_statistics(stats_data)
    print(f"\nStats data: {stats_data}")
    print(f"Average: {avg}, Min: {min_val}, Max: {max_val}")


if __name__ == "__main__":
    main()
