"""Differential tests: the compiled Rust must behave exactly like Python."""
import array
import math
import warnings

import pytest

import copperhead as cp
from copperhead.jit import CopperheadWarning, rust_available

pytestmark = pytest.mark.skipif(not rust_available(), reason="rustc not installed")

BIG = 2 ** 70
GLOBAL_K = 7


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return (math.isnan(a) and math.isnan(b)) or (a == b and math.copysign(1, a) == math.copysign(1, b))
    return type(a) is type(b) and a == b


def outcome(f, *args):
    try:
        return ("ok", f(*args))
    except Exception as e:  # noqa: BLE001
        return ("err", type(e))


def check(jf, cases):
    """Run each case through python and the jit; results/exceptions must agree."""
    for args in cases:
        e = outcome(jf.py_func, *args)
        g = outcome(jf, *args)
        assert e[0] == g[0], (args, e, g)
        if e[0] == "ok":
            assert same(e[1], g[1]), (args, e, g)
        else:
            assert e[1] is g[1], (args, e, g)


def compiled(jf, *args):
    before = jf.native_calls
    jf(*args)
    return jf.native_calls == before + 1


INTS = [0, 1, -1, 2, -2, 3, 7, -7, 10, 100, -100, 2 ** 62, -(2 ** 62), 2 ** 63 - 1, -(2 ** 63), BIG]
FLOATS = [0.0, -0.0, 1.5, -1.5, 2.5, 1e308, -1e308, 1e-320, float("inf"), float("-inf"), float("nan"), 0.1]


@cp.jit(strict=True)
def arith_i(a, b):
    return a + b * 3 - (a // 2) + (a % 5) - (-a)


@cp.jit(strict=True)
def floordiv_i(a, b):
    return a // b


@cp.jit(strict=True)
def mod_i(a, b):
    return a % b


@cp.jit(strict=True)
def floordiv_f(a, b):
    return a // b


@cp.jit(strict=True)
def mod_f(a, b):
    return a % b


@cp.jit(strict=True)
def truediv(a, b):
    return a / b


@cp.jit(strict=True)
def pow_const(a):
    return a ** 3


@cp.jit(strict=True)
def pow_f(a, b):
    return a ** b


@cp.jit(strict=True)
def shifts(a, b):
    return (a << b) ^ (a >> b)


@cp.jit(strict=True)
def mixed(a, b):
    return a * b + 1


def test_integer_semantics_match_python():
    cases = [(a, b) for a in INTS for b in INTS if abs(b) < 2 ** 40 or b in (0, 2 ** 63 - 1, -(2 ** 63), BIG)]
    check(arith_i, [(a, b) for a in INTS[:12] for b in (1, 2, -3)])
    for f in (floordiv_i, mod_i):
        check(f, cases)
    assert compiled(floordiv_i, -7, 2)
    assert floordiv_i(-7, 2) == -4 and mod_i(-7, 2) == 1 and mod_i(7, -2) == -1
    assert floordiv_i(-(2 ** 63), -1) == 2 ** 63  # overflow -> falls back, Python big int
    with pytest.raises(ZeroDivisionError):
        floordiv_i(1, 0)


def test_float_semantics_match_python():
    cases = [(a, b) for a in FLOATS for b in FLOATS]
    for f in (floordiv_f, mod_f, truediv):
        check(f, cases)
    check(mixed, [(3, 2.5), (2.5, 3), (2 ** 62, 1.5)])
    assert mod_f(-7.5, 2.0) == 0.5 and floordiv_f(-7.5, 2.0) == -4.0
    assert compiled(mod_f, 5.0, 3.0)


def test_pow_and_shifts():
    check(pow_const, [(x,) for x in INTS + FLOATS])
    check(pow_f, [(a, b) for a in (0.0, 2.0, -2.0, 1.5, -1.5, 10.0, 1e200) for b in (0.0, 2.0, -3.0, 0.5, 400.0, 1e10)])
    check(shifts, [(a, b) for a in (0, 1, -1, 5, -5, 2 ** 40) for b in (0, 1, 5, 62, 63, 64, 100, -1)])
    assert pow_const(3) == 27 and pow_const(2 ** 22) == 2 ** 66  # overflow falls back to bigint


@cp.jit(strict=True)
def chained(a, b, c):
    return a < b < c


@cp.jit(strict=True)
def cond_loops(n):
    total = 0
    i = 0
    while i < n:
        i += 1
        if i % 3 == 0:
            continue
        if i > 50:
            break
        total += i
    for j in range(n, 0, -2):
        total += j
    for k in range(2, n):
        total -= k
    return total


@cp.jit(strict=True)
def range_step(a, b, c):
    t = 0
    for i in range(a, b, c):
        t = t * 3 + i
    return t


def test_control_flow():
    check(chained, [(a, b, c) for a in (1, 2, 3) for b in (1, 2, 3) for c in (1, 2, 3)])
    check(chained, [(1.0, 2.5, 3.0), (3.0, float("nan"), 4.0)])
    check(cond_loops, [(n,) for n in (-3, 0, 1, 5, 20, 100)])
    check(range_step, [(a, b, c) for a in (-5, 0, 3) for b in (-4, 0, 9) for c in (1, 2, -1, -3, 0)])


@cp.jit(strict=True)
def list_sum(xs):
    s = 0
    for x in xs:
        s += x
    return s


@cp.jit(strict=True)
def float_total(xs):
    s = 0.0
    for i in range(len(xs)):
        s += xs[i] * 0.5
    return s


@cp.jit(strict=True)
def neg_index(xs, i):
    return xs[i] + xs[-1]


@cp.jit(strict=True)
def sieve(n):
    flags = [1] * (n + 1)
    flags[0] = 0
    if n >= 1:
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


@cp.jit(strict=True)
def squares(n):
    out: list[int] = []
    for i in range(n):
        out.append(i * i)
    return out[n - 1] + len(out)


def test_lists():
    check(list_sum, [([1, 2, 3],), ([-5],), ([2 ** 62, 2 ** 62],), (array.array("q", [4, 5]),)])
    check(float_total, [([1.0, 2.5],), ([0.1] * 10,)])
    check(neg_index, [([1, 2, 3], i) for i in (-4, -3, -1, 0, 2, 3, 99)])
    check(sieve, [(n,) for n in (0, 1, 2, 10, 100, 1000)])
    check(squares, [(n,) for n in (0, 1, 5)])
    assert compiled(list_sum, [1, 2, 3])


def test_list_args_not_mutated_and_mixed_lists_fall_back():
    xs = [1, 2, 3]
    list_sum(xs)
    assert xs == [1, 2, 3]
    assert list_sum([1, 2.5]) == 3.5  # mixed list: Python semantics preserved
    assert list_sum([True, 2]) == 3


@cp.jit(strict=True)
def uses_global(x):
    return x * GLOBAL_K


def test_globals_are_guarded():
    global GLOBAL_K
    assert uses_global(2) == 14
    GLOBAL_K = 9
    try:
        assert uses_global(2) == 18  # not the stale compiled constant
    finally:
        GLOBAL_K = 7


@cp.jit(strict=True)
def calls_other(n):
    return fib_ann(n) + helper(n, 2.0)


@cp.jit
def helper(n, f):
    return n * f


@cp.jit
def fib_ann(n) -> int:
    if n < 2:
        return n
    return fib_ann(n - 1) + fib_ann(n - 2)


@cp.jit(strict=True)
def fib_plain(n):
    if n < 2:
        return n
    return fib_plain(n - 1) + fib_plain(n - 2)


@cp.jit(strict=True)
def deep(n):
    if n == 0:
        return 0
    return 1 + deep(n - 1)


def test_calls_and_recursion():
    check(calls_other, [(10,), (0,)])
    check(fib_plain, [(n,) for n in range(15)])
    assert compiled(fib_plain, 20)
    assert deep(500) == 500
    with pytest.raises(RecursionError):  # native depth guard hands over to Python
        deep(100000)


@cp.jit(strict=True)
def math_fn(x):
    return math.sqrt(x) + math.sin(x) + math.floor(x) + math.log(x) + math.atan2(x, 2.0)


@cp.jit(strict=True)
def math_exp(x):
    return math.exp(x)


@cp.jit(strict=True)
def minmax_abs(a, b):
    return max(a, b) - min(a, b) + abs(a)


@cp.jit(strict=True)
def casts(x):
    return int(x) + int(x * 0.5) + float(int(x))


def test_math_and_builtins():
    check(math_fn, [(x,) for x in (0.5, 1.0, 4.0, 100, 0.0, -1.0, float("inf"), float("nan"))])
    check(math_exp, [(x,) for x in (0.0, 1.0, 709.0, 710.0, -800.0, float("nan"), float("inf"))])
    check(minmax_abs, [(a, b) for a in (-3, 0, 4) for b in (-5, 0, 9)])
    check(minmax_abs, [(a, b) for a in (-3.5, 0.0, float("nan")) for b in (-5.5, float("nan"), 9.0)])
    check(casts, [(x,) for x in (3.7, -3.7, 1e300, float("nan"), float("inf"), 5, -9)])


def test_bool_and_conditions():
    @cp.jit(strict=True)
    def f(a, b):
        if a > 0 and b > 0 or not (a < -5):
            return 1
        return 0

    check(f, [(a, b) for a in (-9, -1, 0, 3) for b in (-1, 0, 2)])

    @cp.jit(strict=True)
    def g(flag, n):
        return n if flag else -n

    check(g, [(True, 4), (False, 4)])
    assert same(g(True, 4), 4)


# ----- fallback / honesty ----------------------------------------------------
def test_unsupported_runs_python_with_one_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        @cp.jit
        def uses_print(x):
            print("hi", x)
            return x

        assert uses_print(3) == 3
        assert uses_print(4) == 4
    assert len([x for x in w if issubclass(x.category, CopperheadWarning)]) == 1
    assert "plain Python" in str(w[0].message)


def test_strict_raises():
    @cp.jit(strict=True)
    def bad(xs):
        return [x for x in xs]

    with pytest.raises(cp.Unsupported):
        bad([1, 2])


@pytest.mark.parametrize("src, args", [
    ("def f(x):\n    try:\n        return 1 // x\n    except ZeroDivisionError:\n        return 0\n", (0,)),
    ("def f(x):\n    with open(__file__) as fh:\n        return 1\n", (0,)),
    ("def f(x):\n    return isinstance(x, str)\n", (1,)),
    ("def f(x):\n    return x and 5\n", (3,)),
    ("def f(x):\n    y = 1\n    y = 2.5\n    return y\n", (1,)),
    ("def f(x):\n    return hash(x)\n", (1,)),
])
def test_semantics_we_cannot_reproduce_are_rejected_not_miscompiled(src, args, tmp_path):
    import importlib.util
    f = tmp_path / "mod_under_test.py"
    f.write_text(src)
    spec = importlib.util.spec_from_file_location("mod_under_test", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    strict = cp.jit(mod.f, strict=True)
    with pytest.raises(cp.Unsupported):
        strict(*args)
    lax = cp.jit(mod.f, warn=False)  # lax mode: identical to Python
    assert same(lax(*args), mod.f(*args))
    assert not compiled(lax, *args)


def test_explain_and_rust_source():
    assert "compiled to Rust" in fib_plain.explain(5)
    assert "cp_fib_plain" in fib_plain.rust_source(5)


def test_threads_run_in_parallel_without_gil():
    import threading
    out = []

    @cp.jit(strict=True)
    def work(n):
        t = 0
        for i in range(n):
            t = (t + i * i) % 1000003
        return t

    work(10)
    ts = [threading.Thread(target=lambda: out.append(work(3_000_000))) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(set(out)) == 1 and len(out) == 4
