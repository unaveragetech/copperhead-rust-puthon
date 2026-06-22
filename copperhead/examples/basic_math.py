"""
Basic math operations example for Copperhead.
"""

import copperhead as cp


@cp.compile(target="rust")
def add(x: cp.f64, y: cp.f64) -> cp.f64:
    """Add two floating point numbers."""
    return x + y


@cp.compile(target="rust")
def multiply(x: cp.f64, y: cp.f64) -> cp.f64:
    """Multiply two floating point numbers."""
    return x * y


@cp.compile(target="rust")
def square(x: cp.f64) -> cp.f64:
    """Square a number."""
    return x * x


@cp.compile(target="rust")
def power(base: cp.f64, exponent: cp.f64) -> cp.f64:
    """Calculate base raised to exponent."""
    return cp.math.pow(base, exponent)


@cp.compile(target="rust")
def square_root(x: cp.f64) -> cp.f64:
    """Calculate square root."""
    return cp.math.sqrt(x)


@cp.compile(target="rust")
def absolute_value(x: cp.f64) -> cp.f64:
    """Calculate absolute value."""
    return cp.math.abs(x)


@cp.compile(target="rust")
def min_value(a: cp.f64, b: cp.f64) -> cp.f64:
    """Return the minimum of two values."""
    return cp.math.min(a, b)


@cp.compile(target="rust")
def max_value(a: cp.f64, b: cp.f64) -> cp.f64:
    """Return the maximum of two values."""
    return cp.math.max(a, b)


# These functions run as normal Python
def main():
    """Main function demonstrating the compiled functions."""
    print("Copperhead Basic Math Example")
    print("=" * 40)
    
    a = 5.0
    b = 3.0
    
    print(f"a = {a}, b = {b}")
    print(f"add(a, b) = {add(a, b)}")
    print(f"multiply(a, b) = {multiply(a, b)}")
    print(f"square(a) = {square(a)}")
    print(f"power(a, b) = {power(a, b)}")
    print(f"square_root(a) = {square_root(a)}")
    print(f"absolute_value(-a) = {absolute_value(-a)}")
    print(f"min_value(a, b) = {min_value(a, b)}")
    print(f"max_value(a, b) = {max_value(a, b)}")


if __name__ == "__main__":
    main()
