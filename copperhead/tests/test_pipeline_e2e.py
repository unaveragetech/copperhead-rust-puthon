"""End-to-end regression tests for the PyO3 build pipeline (compiler.py / transpiler.py / parser.py).

Each test corresponds to a defect from the source audit and passes only once the defect is fixed.
"""
import importlib.machinery
import importlib.util
import os
import shutil
import sys

import pytest

import copperhead as cp
from copperhead.compiler import (BuildConfig, CompilationMode, CompilationStatus, CopperheadCompiler,
                                 compile_directory)
from copperhead.parser import parse_source
from copperhead.transpiler import TranspileError, transpile_module, transpile_source

HAVE_CARGO = shutil.which("cargo") is not None


def load_ext(path, name):
    loader = importlib.machinery.ExtensionFileLoader(name, str(path))
    spec = importlib.util.spec_from_file_location(name, str(path), loader=loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not HAVE_CARGO, reason="cargo not installed")
def test_bundle_builds_and_imports(tmp_path):
    """Audit #4 (NameError in bundle), #63 (lib.rs location), #64 (module name), #65 (.pyd), #66-68."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.py").write_text(
        "import copperhead as cp\n\n@cp.compile\ndef add(a: cp.i64, b: cp.i64) -> cp.i64:\n    return a + b\n")
    (proj / "b.py").write_text(
        "import copperhead as cp\n\n@cp.compile(target='rust')\ndef sq(x: cp.f64) -> cp.f64:\n    return x * x\n")
    r = compile_directory(str(proj), mode=CompilationMode.BUNDLE, build_dir=str(tmp_path / "build"),
                          cache_dir=str(tmp_path / "cache"), output_name="my-bundle")
    assert r.status == CompilationStatus.SUCCESS, r.error_message
    assert r.output_path.endswith(".pyd" if sys.platform == "win32" else ".so")
    assert (tmp_path / "build" / "my_bundle" / "src" / "lib.rs").exists()
    mod = load_ext(r.output_path, "my_bundle")
    assert mod.add(2, 3) == 5 and mod.sq(1.5) == 2.25


def test_bundle_name_collision_is_an_error(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    for n in ("a", "b"):
        (proj / f"{n}.py").write_text(
            "import copperhead as cp\n\n@cp.compile\ndef f(x: cp.i64) -> cp.i64:\n    return x\n")
    r = compile_directory(str(proj), mode=CompilationMode.BUNDLE, build_dir=str(tmp_path / "build"),
                          cache_dir=str(tmp_path / "cache"))
    assert r.status == CompilationStatus.FAILED and "collision" in r.error_message


def test_cache_key_is_content_based_not_mtime(tmp_path):
    """Audit #5/#75: same path + same mtime but different content must not share a cache entry."""
    f = tmp_path / "m.py"
    f.write_text("x = 1\n")
    st = f.stat()
    c = CopperheadCompiler(BuildConfig(source_path=str(f), build_dir=str(tmp_path / "b"),
                                       cache_dir=str(tmp_path / "c")))
    k1 = c._get_cache_key(f)
    f.write_text("x = 2\n")
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))  # preserve the timestamp
    assert c._get_cache_key(f) != k1


def test_bare_decorators_are_recognised():
    """`@cp.compile` (no parentheses) and `@cp.jit` were ignored by the parser."""
    src = ("import copperhead as cp\n"
           "@cp.compile\ndef a(x: cp.i64) -> cp.i64:\n    return x\n"
           "@cp.jit\ndef b(x: cp.i64) -> cp.i64:\n    return x\n"
           "@cp.compile()\ndef c(x: cp.i64) -> cp.i64:\n    return x\n"
           "def d(x: cp.i64) -> cp.i64:\n    return x\n")
    assert [f.name for f in parse_source(src).functions if f.is_rpb] == ["a", "b", "c"]


def test_no_invalid_dyn_pyobject_types():
    """Audit #41: `Box<dyn PyObject>` is not valid Rust (PyObject is a concrete type)."""
    from copperhead.parser import TYPE_MAPPINGS
    assert all("dyn PyObject" not in t.rust_type for t in TYPE_MAPPINGS.values())


def test_module_name_matches_requested_name():
    src = "import copperhead as cp\n\n@cp.compile\ndef f(x: cp.i64) -> cp.i64:\n    return x\n"
    rust = transpile_module(parse_source(src), module_name="mylib")
    assert "fn mylib(m: &Bound" in rust and "_copperhead_module" not in rust


@pytest.mark.parametrize("body, needle", [
    ("    try:\n        return 1\n    except Exception:\n        return 0\n", "try"),
    ("    with open('f') as fh:\n        return 1\n", "with"),
    ("    return isinstance(x, str)\n", "isinstance"),
    ("    yield x\n", "yield"),
    ("    return hash(x)\n", "hash"),
])
def test_strict_mode_refuses_to_emit_semantic_placeholders(body, needle):
    """Audit #6-9,#11-13,#48-51: unsupported constructs must be an error, never silent comments."""
    src = f"import copperhead as cp\n\n@cp.compile\ndef f(x: cp.i64) -> cp.i64:\n{body}"
    with pytest.raises(TranspileError) as e:
        transpile_module(parse_source(src), strict=True)
    assert needle in str(e.value)


def test_string_and_list_builtins_are_not_the_old_wrong_mappings():
    rust = transpile_source(
        "import copperhead as cp\n\n@cp.compile\n"
        "def f(s: cp.str) -> cp.str:\n    return s.center(11)\n")
    assert ".take(11 as usize)" not in rust and "__p" in rust  # really pads
    rust = transpile_source(
        "import copperhead as cp\n\n@cp.compile\n"
        "def g(xs: list[cp.i64]) -> cp.i64:\n    xs.remove(3)\n    return xs.index(2)\n")
    assert "retain" not in rust and "unwrap_or(-1)" not in rust


def test_import_hook_is_opt_in_and_does_not_hijack_imports():
    """Audit #2/#3: importing copperhead must not install a catch-all finder."""
    assert not any(type(f).__name__ == "CopperheadImporter" for f in sys.meta_path)
    imp = cp.install_importer()
    try:
        assert imp.find_spec("json", None) is None  # unknown modules are never claimed
        assert imp.find_spec("some_unregistered_module", None) is None
    finally:
        cp.uninstall_importer()


def test_decorator_really_compiles():
    """Audit #1: `@cp.compile` used to only set attributes; calling it still ran Python."""
    if not cp.rust_available():
        pytest.skip("rustc missing")

    @cp.compile
    def tri(n):
        t = 0
        for i in range(n):
            t += i
        return t

    assert tri(10) == 45
    assert tri.native_calls == 1
