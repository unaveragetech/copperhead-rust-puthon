"""Reproducible @cp.jit vs CPython benchmark.   python benchmarks/jit_bench.py"""
import os, platform, statistics, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import copperhead as cp


def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def collatz_total(limit):
    best = 0
    for start in range(1, limit):
        n, steps = start, 0
        while n != 1:
            n = n // 2 if n % 2 == 0 else 3 * n + 1
            steps += 1
        if steps > best:
            best = steps
    return best


def sieve(n):
    flags = [1] * (n + 1)
    flags[0] = 0
    flags[1] = 0
    i = 2
    while i * i <= n:
        if flags[i]:
            j = i * i
            while j <= n:
                flags[j] = 0
                j += i
        i += 1
    return sum(flags)


def mandel(n):
    count = 0
    for py in range(n):
        for px in range(n):
            x0 = px * 3.5 / n - 2.5
            y0 = py * 2.0 / n - 1.0
            x = 0.0
            y = 0.0
            it = 0
            while x * x + y * y <= 4.0 and it < 100:
                x, y = x * x - y * y + x0, 2.0 * x * y + y0
                it += 1
            count += it
    return count


CASES = [("fib(30)", fib, (30,)), ("collatz(300_000)", collatz_total, (300_000,)),
         ("sieve(5_000_000)", sieve, (5_000_000,)), ("mandelbrot(300)", mandel, (300,))]


def best_of(f, args, runs):
    ts = []
    for _ in range(runs):
        t = time.perf_counter(); r = f(*args); ts.append(time.perf_counter() - t)
    return min(ts), r


if __name__ == "__main__":
    print(f"Python {platform.python_version()} on {platform.platform()}  (best of 3, compile excluded)\n")
    print(f"{'case':<20}{'python':>10}{'copperhead':>12}{'speedup':>10}  result-equal")
    for name, f, args in CASES:
        jf = cp.jit(f, strict=True)
        jf(*args)                      # warm-up: compile (cached on disk) + first call
        tp, rp = best_of(f, args, 3)
        tj, rj = best_of(jf, args, 3)
        assert jf.native_calls >= 3, "benchmark ran in Python, not Rust"
        print(f"{name:<20}{tp*1000:>8.0f}ms{tj*1000:>10.1f}ms{tp/tj:>9.0f}x  {rp == rj}")
