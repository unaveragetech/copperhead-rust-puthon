"""
Copperhead JIT: decorate a Python function, get a native Rust implementation.

    import copperhead as cp

    @cp.jit
    def fib(n):
        if n < 2:
            return n
        return fib(n - 1) + fib(n - 2)

    fib(35)          # first call compiles to Rust (cached on disk), then runs natively

How it works
------------
* On the first call the function is *specialised* on the runtime types of its
  arguments (int / float / bool / list[int] / list[float] / array / numpy 1-D).
* The function body is translated to Rust with **Python semantics** (floor
  division, negative indexing, overflow-checked integer arithmetic, ...).
* The Rust is built with ``rustc`` into a shared library (cached by content hash)
  and called through ``ctypes``.  ``ctypes`` releases the GIL during the call, so
  compiled functions can run truly in parallel on threads.
* Correctness first: any construct the translator cannot reproduce *exactly*
  makes the function fall back to plain Python (one warning, with the reason).
  Anything that goes wrong at run time in native code (integer overflow, zero
  division, bad index, domain errors, ...) re-runs the call in Python so the
  genuine Python result / exception is produced.  Compiled functions must
  therefore be pure (no printing, no I/O, no mutating of their arguments) -
  the translator rejects anything else.
"""

from __future__ import annotations

import array
import ast
import ctypes
import functools
import hashlib
import inspect
import math as _math
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import types
import threading
import warnings
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "jit", "JitFunction", "CopperheadWarning", "Unsupported", "BuildError",
    "rust_available", "clear_cache", "cache_dir",
]

INT, FLOAT, BOOL, LINT, LFLT = "int", "float", "bool", "list[int]", "list[float]"
RS = {INT: "i64", FLOAT: "f64", BOOL: "bool", LINT: "Vec<i64>", LFLT: "Vec<f64>"}
ELEM = {LINT: INT, LFLT: FLOAT}
LISTOF = {INT: LINT, FLOAT: LFLT}
SCALARS = (INT, FLOAT, BOOL)
MAX_I64 = 2 ** 63 - 1
MIN_I64 = -(2 ** 63)
ALL = None  # sentinel: "every variable is defined" (unreachable code)


class CopperheadWarning(UserWarning):
    """Emitted (once per function) when a function falls back to Python."""


class Unsupported(Exception):
    """The function uses something that cannot be translated exactly."""


class BuildError(Exception):
    """rustc failed or is unavailable."""


class _NeedRet(Exception):
    def __init__(self, key):
        self.key = key


# ─────────────────────────────────────────────────────────────────────────────
# Rust prelude (helpers that reproduce Python semantics)
# ─────────────────────────────────────────────────────────────────────────────
PRELUDE = r'''#![allow(unused, non_snake_case, unused_mut, unused_parens, unused_assignments,
         unused_variables, dead_code, unreachable_code, overflowing_literals)]
type R<T> = Result<T, i32>;
#[inline(always)] fn ck<T>(o: Option<T>) -> R<T> { o.ok_or(1) }
#[inline(always)] fn fdiv_i(a: i64, b: i64) -> R<i64> {
    if b == 0 { return Err(3); }
    let q = a.checked_div(b).ok_or(1)?;
    let r = a % b;
    if r != 0 && ((r < 0) != (b < 0)) { ck(q.checked_sub(1)) } else { Ok(q) }
}
#[inline(always)] fn mod_i(a: i64, b: i64) -> R<i64> {
    if b == 0 { return Err(3); }
    if b == -1 { return Ok(0); }
    let r = a % b;
    if r != 0 && ((r < 0) != (b < 0)) { Ok(r + b) } else { Ok(r) }
}
#[inline(always)] fn div_f(a: f64, b: f64) -> R<f64> { if b == 0.0 { Err(3) } else { Ok(a / b) } }
fn divmod_f(a: f64, b: f64) -> R<(f64, f64)> {
    if b == 0.0 { return Err(3); }
    let mut m = a % b;
    let mut d = (a - m) / b;
    if m != 0.0 {
        if (b < 0.0) != (m < 0.0) { m += b; d -= 1.0; }
    } else {
        m = 0.0f64.copysign(b);
    }
    let fd;
    if d != 0.0 {
        let f = d.floor();
        fd = if d - f > 0.5 { f + 1.0 } else { f };
    } else {
        fd = 0.0f64.copysign(a / b);
    }
    Ok((fd, m))
}
#[inline(always)] fn fdiv_f(a: f64, b: f64) -> R<f64> { Ok(divmod_f(a, b)?.0) }
#[inline(always)] fn mod_f(a: f64, b: f64) -> R<f64> { Ok(divmod_f(a, b)?.1) }
fn pow_f(a: f64, b: f64) -> R<f64> {
    if a == 0.0 && b < 0.0 { return Err(3); }
    if a < 0.0 && a.is_finite() && b.is_finite() && b.fract() != 0.0 { return Err(2); }
    let r = a.powf(b);
    if r.is_infinite() && a.is_finite() && b.is_finite() { return Err(1); }
    Ok(r)
}
#[inline(always)] fn ix(i: i64, n: usize) -> R<usize> {
    let j = if i < 0 { i + n as i64 } else { i };
    if j < 0 || j >= n as i64 { Err(4) } else { Ok(j as usize) }
}
#[inline(always)] fn f2i(x: f64) -> R<i64> {
    if !x.is_finite() || x >= 9.223372036854775807e18 || x < -9.223372036854775808e18 { Err(1) } else { Ok(x as i64) }
}
#[inline(always)] fn mc(r: f64, any_nan: bool, all_finite: bool) -> R<f64> {
    if r.is_nan() && !any_nan { return Err(2); }
    if r.is_infinite() && all_finite { return Err(1); }
    Ok(r)
}
fn sum_i(v: &[i64]) -> R<i64> {
    let mut s = 0i64;
    for &x in v { s = s.checked_add(x).ok_or(1)?; }
    Ok(s)
}
fn mk_vec<T: Clone>(x: T, n: i64) -> R<Vec<T>> {
    if n <= 0 { return Ok(Vec::new()); }
    if n > (1i64 << 28) { return Err(1); }
    Ok(vec![x; n as usize])
}
'''

MAX_DEPTH = 1500  # native recursion depth before handing back to Python


# ─────────────────────────────────────────────────────────────────────────────
# Translator
# ─────────────────────────────────────────────────────────────────────────────
_CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}

_MATH_CONST = {"pi": _math.pi, "e": _math.e, "tau": _math.tau}
_MATH_FN1 = {  # name -> rust method
    "sqrt": "sqrt", "sin": "sin", "cos": "cos", "tan": "tan", "atan": "atan",
    "exp": "exp", "log2": "log2", "log10": "log10", "asin": "asin", "acos": "acos",
    "sinh": "sinh", "cosh": "cosh", "tanh": "tanh",
}


def _fmt_float(v: float) -> str:
    if v != v:
        return "f64::NAN"
    if v in (float("inf"), float("-inf")):
        return "f64::INFINITY" if v > 0 else "f64::NEG_INFINITY"
    r = repr(v)
    if "e" not in r and "." not in r:
        r += ".0"
    return f"({r}f64)"


def _ann_to_type(ann) -> Optional[str]:
    if ann is int:
        return INT
    if ann is float:
        return FLOAT
    if ann is bool:
        return BOOL
    if isinstance(ann, str):
        s = ann.replace(" ", "")
        if s in ("int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize", "isize",
                 "cp.i64", "cp.i32", "cp.u32", "cp.u64", "cp.usize"):
            return INT
        if s in ("float", "f32", "f64", "cp.f64", "cp.f32"):
            return FLOAT
        if s == "bool":
            return BOOL
    return None


def _free_lookup(py, name: str):
    """Resolve a non-local name for function `py`: closure cell, then module globals."""
    code = py.__code__
    if name in code.co_freevars and py.__closure__:
        cell = py.__closure__[code.co_freevars.index(name)]
        try:
            return True, cell.cell_contents
        except ValueError:
            return False, None
    g = py.__globals__
    if name in g:
        return True, g[name]
    return False, None


class _Unit:
    def __init__(self, name, jf, argtypes, ret):
        self.name = name
        self.jf = jf
        self.argtypes = argtypes
        self.ret = ret
        self.code = ""
        self.leaf = True
        self.guards: List[Tuple[str, Any]] = []


class _Crate:
    """One Rust compilation unit = one root specialisation + every callee it needs."""

    def __init__(self):
        self.units: Dict[Tuple[int, Tuple[str, ...]], _Unit] = {}
        self.counter = 0
        self.guards: List[Tuple[str, Any]] = []

    def unit_for(self, jf: "JitFunction", argtypes: Tuple[str, ...], caller_key=None) -> _Unit:
        key = (id(jf), argtypes)
        if key in self.units:
            u = self.units[key]
            if u.ret is None:
                raise _NeedRet(key)
            return u
        return self._build(jf, argtypes, key)

    def _build(self, jf, argtypes, key) -> _Unit:
        if jf._tree is None:
            raise Unsupported(f"callee '{jf.__name__}': {jf._reasons.get((), 'source not available')}")
        self.counter += 1
        name = f"cp_{jf.__name__}_{self.counter}"
        ann_ret = _ann_to_type(jf._py.__annotations__.get("return")) if hasattr(jf._py, "__annotations__") else None
        unit = _Unit(name, jf, argtypes, ann_ret)
        self.units[key] = unit
        candidates = [ann_ret] if ann_ret else [None, INT, FLOAT, BOOL]
        snapshot = dict(self.units)
        guard_snapshot = list(self.guards)
        first_err: Optional[Exception] = None
        for cand in candidates:
            unit.ret = cand
            unit.leaf = True
            try:
                gen = _FnGen(self, jf, argtypes, unit, fixed_ret=cand)
                unit.code = gen.generate()
                unit.ret = gen.ret
                return unit
            except _NeedRet as nr:
                if nr.key != key:
                    del self.units[key]
                    raise Unsupported("mutually recursive functions need return annotations "
                                      "(e.g. `-> int`)")
            except Unsupported as e:
                if cand is None or ann_ret:
                    del self.units[key]
                    raise
                first_err = first_err or e
            self.units = dict(snapshot)
            self.units[key] = unit
            self.guards = list(guard_snapshot)
        del self.units[key]
        raise Unsupported("recursive function: add a return annotation (e.g. `-> int`)"
                          + (f" [{first_err}]" if first_err else ""))


class _FnGen:
    def __init__(self, crate: _Crate, jf: "JitFunction", argtypes, unit: _Unit, fixed_ret):
        self.crate = crate
        self.jf = jf
        self.unit = unit
        self.tree: ast.FunctionDef = jf._tree
        self.argtypes = argtypes
        self.fixed_ret = fixed_ret
        self.ret: Optional[str] = fixed_ret
        self.vars: Dict[str, str] = {}
        self.defined: Optional[set] = set()
        self.tmp = 0
        a = self.tree.args
        if a.vararg or a.kwarg or a.kwonlyargs:
            raise Unsupported("*args / **kwargs / keyword-only arguments")
        self.params = [x.arg for x in a.posonlyargs + a.args]
        if len(self.params) != len(argtypes):
            raise Unsupported("argument count mismatch")
        self.arg_set = set(self.params)
        self.mutated_lists = self._scan_mutations()
        self.loop_depth = 0
        for p, t in zip(self.params, argtypes):
            self.vars[p] = t
            self.defined.add(p)

    # ---- helpers ------------------------------------------------------------
    def _scan_mutations(self) -> set:
        names = set()
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in targets:
                    for sub in ast.walk(t):
                        if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
                            names.add(sub.value.id)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and isinstance(n.func.value, ast.Name) and n.func.attr == "append":
                names.add(n.func.value.id)
            elif isinstance(n, ast.Delete):
                raise Unsupported("del statement")
        return names

    def fresh(self, base="t"):
        self.tmp += 1
        return f"__{base}{self.tmp}"

    def err(self, node, msg):
        line = getattr(node, "lineno", None)
        where = f" (line {line + self.jf._line_offset})" if line else ""
        raise Unsupported(f"{msg}{where}")

    def lookup_free(self, name: str):
        """Resolve a non-local name to a Python object (closure, then globals)."""
        return _free_lookup(self.jf._py, name)

    # ---- generate -----------------------------------------------------------
    def generate(self) -> str:
        lines, defined, term = self.block(self.tree.body)
        if not term:
            self.err(self.tree, "function can reach its end without returning a value")
        if self.ret is None:
            self.err(self.tree, "function never returns a value")
        sig = []
        for p, t in zip(self.params, self.argtypes):
            sig.append(f"mut {p}: {RS[t]}" if t in SCALARS else f"{p}: &[{RS[ELEM[t]]}]")
        sig.append("__d: u32")
        decls = []
        for v, t in self.vars.items():
            if v in self.arg_set:
                continue
            init = {INT: "0", FLOAT: "0.0", BOOL: "false"}.get(t, "Vec::new()")
            decls.append(f"    let mut {v}: {RS[t]} = {init};")
        head = f"fn {self.unit.name}({', '.join(sig)}) -> R<{RS[self.ret]}> {{\n"
        if not self.unit.leaf:
            head += f"    if __d > {MAX_DEPTH} {{ return Err(5); }}\n"
        body = "\n".join("    " + l for l in lines)
        return head + "\n".join(decls) + ("\n" if decls else "") + body + "\n    Err(1)\n}\n"

    # ---- statements ---------------------------------------------------------
    def block(self, stmts, ) -> Tuple[List[str], Optional[set], bool]:
        out: List[str] = []
        term = False
        for i, s in enumerate(stmts):
            if term:
                break  # unreachable remainder: ignore like Python would never run it
            if i == 0 and isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) \
                    and isinstance(s.value.value, str):
                continue  # docstring
            lines, t = self.stmt(s)
            out.extend(lines)
            term = term or t
        return out, (ALL if term else (None if self.defined is ALL else set(self.defined))), term

    @staticmethod
    def _meet(a, b):
        if a is ALL:
            return b
        if b is ALL:
            return a
        return a & b

    def declare(self, node, name, typ):
        old = self.vars.get(name)
        if old is None:
            self.vars[name] = typ
        elif old != typ:
            self.err(node, f"variable '{name}' changes type from {old} to {typ}; "
                           f"keep one type per variable (e.g. initialise with 0.0 for floats)")
        if self.defined is not ALL:
            self.defined.add(name)

    def stmt(self, s) -> Tuple[List[str], bool]:
        m = getattr(self, "s_" + type(s).__name__, None)
        if m is None:
            self.err(s, f"unsupported statement '{type(s).__name__}'")
        return m(s)

    def s_Pass(self, s):
        return [], False

    def s_Break(self, s):
        if not self.loop_depth:
            self.err(s, "break outside loop")
        return ["break;"], True

    def s_Continue(self, s):
        if not self.loop_depth:
            self.err(s, "continue outside loop")
        return ["continue;"], True

    def s_Raise(self, s):
        return ["return Err(1);"], True

    def s_Assert(self, s):
        return [f"if !({self.truth(s.test)}) {{ return Err(1); }}"], False

    def s_Expr(self, s):
        v = s.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "append" \
                and isinstance(v.func.value, ast.Name):
            nm = v.func.value.id
            t = self.vars.get(nm)
            if t not in ELEM or nm in self.arg_set:
                self.err(s, "append is only supported on lists created inside the function")
            if len(v.args) != 1 or v.keywords:
                self.err(s, "append takes one argument")
            c, ct = self.ex(v.args[0])
            if ct != ELEM[t]:
                self.err(s, f"cannot append {ct} to {t}")
            self.need_defined(nm, s)
            return [f"{nm}.push({c});"], False
        self.err(s, "expression statements (calls with side effects, print, ...) are not supported")

    def s_Return(self, s):
        if s.value is None:
            self.err(s, "bare return (returns None)")
        c, t = self.ex(s.value)
        if t not in SCALARS:
            self.err(s, "only int / float / bool return values are supported")
        if self.ret is None:
            self.ret = t
        elif self.ret != t:
            self.err(s, f"function returns both {self.ret} and {t}; return one consistent type")
        return [f"return Ok({c});"], True

    def need_defined(self, name, node):
        if self.defined is not ALL and name not in self.defined:
            self.err(node, f"variable '{name}' may be used before assignment")

    def assign_value(self, node, target, value) -> List[str]:
        if isinstance(target, ast.Name):
            nm = target.id
            return self.assign_name(node, nm, value)
        if isinstance(target, ast.Subscript):
            if not isinstance(target.value, ast.Name):
                self.err(node, "unsupported subscript assignment")
            nm = target.value.id
            t = self.vars.get(nm)
            if t not in ELEM:
                self.err(node, f"'{nm}' is not a list")
            if nm in self.arg_set:
                self.err(node, f"mutating argument '{nm}' is not supported (it would change the caller's list)")
            self.need_defined(nm, node)
            ic, it = self.ex(target.slice)
            if it != INT:
                self.err(node, "list index must be int")
            vc, vt = self.ex(value)
            if vt != ELEM[t]:
                self.err(node, f"cannot store {vt} into {t}")
            k = self.fresh("i")
            return [f"let {k} = ix({ic}, {nm}.len())?;", f"{nm}[{k}] = {vc};"]
        self.err(node, "unsupported assignment target")

    def assign_name(self, node, nm, value) -> List[str]:
        if isinstance(value, ast.List) or (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult)
                                          and (isinstance(value.left, ast.List) or isinstance(value.right, ast.List))):
            code, t = self.list_expr(value, self.vars.get(nm))
            if nm in self.arg_set:
                self.err(node, f"rebinding list argument '{nm}' is not supported")
            self.declare(node, nm, t)
            return [f"{nm} = {code};"]
        c, t = self.ex(value)
        if t in ELEM:
            self.err(node, "assigning one list variable to another (aliasing) is not supported")
        self.declare(node, nm, t)
        return [f"{nm} = {c};"]

    def list_expr(self, value, hint=None):
        if isinstance(value, ast.List):
            if not value.elts:
                if hint in ELEM:
                    return "Vec::new()", hint
                self.err(value, "empty list literal needs a type: write `x: list[int] = []`")
            codes = [self.ex(e) for e in value.elts]
            et = codes[0][1]
            if et not in LISTOF or any(t != et for _, t in codes):
                self.err(value, "list literals must contain only ints or only floats")
            return f"vec![{', '.join(c for c, _ in codes)}]", LISTOF[et]
        left, right = value.left, value.right
        lst, cnt = (left, right) if isinstance(left, ast.List) else (right, left)
        if len(lst.elts) != 1:
            self.err(value, "only [x] * n list repetition is supported")
        ec, et = self.ex(lst.elts[0])
        if et not in LISTOF:
            self.err(value, "list elements must be int or float")
        cc, ct = self.ex(cnt)
        if ct != INT:
            self.err(value, "list repetition count must be int")
        return f"mk_vec({ec}, {cc})?", LISTOF[et]

    def s_Assign(self, s):
        lines: List[str] = []
        if len(s.targets) == 1 and isinstance(s.targets[0], ast.Tuple):
            tgt = s.targets[0]
            if not isinstance(s.value, ast.Tuple) or len(s.value.elts) != len(tgt.elts) \
                    or not all(isinstance(e, ast.Name) for e in tgt.elts):
                self.err(s, "only `a, b = x, y` tuple assignment is supported")
            tmps = []
            for e in s.value.elts:
                c, t = self.ex(e)
                if t in ELEM:
                    self.err(s, "lists in tuple assignment")
                k = self.fresh("u")
                lines.append(f"let {k} = {c};")
                tmps.append((k, t))
            for e, (k, t) in zip(tgt.elts, tmps):
                self.declare(s, e.id, t)
                lines.append(f"{e.id} = {k};")
            return lines, False
        for t in s.targets:
            lines += self.assign_value(s, t, s.value)
        return lines, False

    def s_AnnAssign(self, s):
        if s.value is None:
            self.err(s, "annotation without value")
        if isinstance(s.target, ast.Name) and isinstance(s.value, ast.List) and not s.value.elts:
            a = ast.unparse(s.annotation).replace(" ", "")
            hint = {"list[int]": LINT, "list[float]": LFLT, "List[int]": LINT, "List[float]": LFLT}.get(a)
            if hint is None:
                self.err(s, "empty list annotation must be list[int] or list[float]")
            self.declare(s, s.target.id, hint)
            return [f"{s.target.id} = Vec::new();"], False
        tgt_t = _ann_to_type(ast.unparse(s.annotation))
        lines = self.assign_value(s, s.target, s.value)
        if tgt_t and isinstance(s.target, ast.Name) and self.vars.get(s.target.id) != tgt_t \
                and self.vars.get(s.target.id) in SCALARS:
            self.err(s, f"value does not match annotation {tgt_t}")
        return lines, False

    def s_AugAssign(self, s):
        load = ast.copy_location(
            ast.Name(id=s.target.id, ctx=ast.Load()) if isinstance(s.target, ast.Name) else
            ast.Subscript(value=s.target.value, slice=s.target.slice, ctx=ast.Load()), s)
        if isinstance(s.target, ast.Name):
            self.need_defined(s.target.id, s)
        binop = ast.copy_location(ast.BinOp(left=load, op=s.op, right=s.value), s)
        return self.assign_value(s, s.target, binop), False

    def s_If(self, s):
        cond = self.truth(s.test)
        d0 = None if self.defined is ALL else set(self.defined)
        l1, d1, t1 = self.block(s.body)
        self.defined = None if d0 is ALL else set(d0)
        l2, d2, t2 = self.block(s.orelse) if s.orelse else ([], (None if d0 is ALL else set(d0)), False)
        self.defined = self._meet(d1, d2)
        out = [f"if {cond} {{"] + ["    " + l for l in l1]
        if l2:
            out += ["} else {"] + ["    " + l for l in l2]
        out.append("}")
        return out, (t1 and t2)

    def s_While(self, s):
        if s.orelse:
            self.err(s, "while/else")
        cond = self.truth(s.test)
        d0 = None if self.defined is ALL else set(self.defined)
        self.loop_depth += 1
        body, _, _ = self.block(s.body)
        self.loop_depth -= 1
        self.defined = d0
        out = ["loop {", f"    if !({cond}) {{ break; }}"] + ["    " + l for l in body] + ["}"]
        infinite = (isinstance(s.test, ast.Constant) and s.test.value is True
                    and not any(isinstance(n, ast.Break) for n in ast.walk(ast.Module(body=s.body, type_ignores=[]))))
        return out, infinite

    def s_For(self, s):
        if s.orelse:
            self.err(s, "for/else")
        if not isinstance(s.target, ast.Name):
            self.err(s, "for-loop target must be a simple name")
        it = s.iter
        tgt = s.target.id
        if isinstance(tgt, str) and tgt in self.arg_set and self.vars[tgt] in ELEM:
            self.err(s, "loop variable shadows a list argument")
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range" \
                and not it.keywords and 1 <= len(it.args) <= 3:
            parts = []
            for a in it.args:
                c, t = self.ex(a)
                if t != INT:
                    self.err(s, "range() arguments must be int")
                parts.append(c)
            if len(parts) == 1:
                start, stop, step = "0", parts[0], "1"
            elif len(parts) == 2:
                start, stop, step = parts[0], parts[1], "1"
            else:
                start, stop, step = parts
            i, e, st, dn = self.fresh("i"), self.fresh("e"), self.fresh("s"), self.fresh("dn")
            d0 = set(self.defined) if self.defined is not ALL else ALL
            self.declare(s, tgt, INT)
            self.loop_depth += 1
            body, _, _ = self.block(s.body)
            self.loop_depth -= 1
            self.defined = d0
            out = ["{", f"    let mut {i}: i64 = {start}; let {e}: i64 = {stop}; let {st}: i64 = {step};",
                   f"    if {st} == 0 {{ return Err(2); }}", f"    let mut {dn} = false;",
                   f"    loop {{", f"        if {dn} || !(if {st} > 0 {{ {i} < {e} }} else {{ {i} > {e} }}) {{ break; }}",
                   f"        {tgt} = {i};",
                   f"        match {i}.checked_add({st}) {{ Some(v) => {i} = v, None => {dn} = true }}"]
            out += ["        " + l for l in body] + ["    }", "}"]
            return out, False
        if isinstance(it, ast.Name) and self.vars.get(it.id) in ELEM:
            lst = it.id
            self.need_defined(lst, s)
            if lst in self.mutated_lists and lst not in self.arg_set:
                self.err(s, f"list '{lst}' is mutated; iterating a list that changes is not supported")
            k = self.fresh("k")
            d0 = set(self.defined) if self.defined is not ALL else ALL
            self.declare(s, tgt, ELEM[self.vars[lst]])
            self.loop_depth += 1
            body, _, _ = self.block(s.body)
            self.loop_depth -= 1
            self.defined = d0
            out = [f"for {k} in 0..{lst}.len() {{", f"    {tgt} = {lst}[{k}];"] + ["    " + l for l in body] + ["}"]
            return out, False
        self.err(s, "for loops must iterate over range(...) or a list variable")

    # ---- expressions --------------------------------------------------------
    def truth(self, node) -> str:
        c, t = self.ex(node)
        if t == BOOL:
            return c
        if t == INT:
            return f"({c} != 0)"
        if t == FLOAT:
            return f"({c} != 0.0)"
        if t in ELEM:
            return f"({c}.len() != 0)"
        self.err(node, "cannot use this value as a condition")

    def ex(self, node) -> Tuple[str, str]:
        m = getattr(self, "e_" + type(node).__name__, None)
        if m is None:
            self.err(node, f"unsupported expression '{type(node).__name__}'")
        return m(node)

    def e_Constant(self, n):
        v = n.value
        if v is True or v is False:
            return ("true" if v else "false"), BOOL
        if type(v) is int:
            if not (MIN_I64 <= v <= MAX_I64):
                self.err(n, "integer constant too large for i64")
            return (f"({v}i64)" if v >= 0 else f"({v}i64)"), INT
        if type(v) is float:
            return _fmt_float(v), FLOAT
        self.err(n, f"unsupported constant {v!r}")

    def e_Name(self, n):
        nm = n.id
        if nm in self.vars:
            self.need_defined(nm, n)
            return nm, self.vars[nm]
        ok, val = self.lookup_free(nm)
        if ok:
            if type(val) is bool:
                self.crate.guards.append((nm, val, self.jf._py))
                return ("true" if val else "false"), BOOL
            if type(val) is int and MIN_I64 <= val <= MAX_I64:
                self.crate.guards.append((nm, val, self.jf._py))
                return f"({val}i64)", INT
            if type(val) is float:
                self.crate.guards.append((nm, val, self.jf._py))
                return _fmt_float(val), FLOAT
        if nm in ("True", "False"):
            return nm.lower(), BOOL
        self.err(n, f"name '{nm}' is not a local variable or a numeric constant")

    def e_UnaryOp(self, n):
        c, t = self.ex(n.operand)
        if isinstance(n.op, ast.Not):
            return f"(!{self.truth(n.operand)})", BOOL
        if t == BOOL:
            self.err(n, "arithmetic on bool")
        if t not in (INT, FLOAT):
            self.err(n, "unary operator on non-number")
        if isinstance(n.op, ast.USub):
            return (f"ck({c}.checked_neg())?", INT) if t == INT else (f"(-{c})", FLOAT)
        if isinstance(n.op, ast.UAdd):
            return c, t
        if isinstance(n.op, ast.Invert) and t == INT:
            return f"(!{c})", INT
        self.err(n, "unsupported unary operator")

    def num_pair(self, n, lc, lt, rc, rt):
        for t in (lt, rt):
            if t not in (INT, FLOAT):
                self.err(n, f"operator not supported for {lt} and {rt}")
        if lt == rt:
            return lc, rc, lt
        lc = f"({lc} as f64)" if lt == INT else lc
        rc = f"({rc} as f64)" if rt == INT else rc
        return lc, rc, FLOAT

    def e_BinOp(self, n):
        if isinstance(n.left, ast.List) or isinstance(n.right, ast.List):
            self.err(n, "list expressions are only supported as the right-hand side of an assignment")
        lc, lt = self.ex(n.left)
        rc, rt = self.ex(n.right)
        op = n.op
        if lt == BOOL and rt == BOOL and isinstance(op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
            s = {ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^"}[type(op)]
            return f"({lc} {s} {rc})", BOOL
        if lt == BOOL or rt == BOOL:
            self.err(n, "arithmetic on bool")
        if isinstance(op, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)):
            if lt != INT or rt != INT:
                self.err(n, "bitwise operators need ints")
            if isinstance(op, ast.BitAnd):
                return f"({lc} & {rc})", INT
            if isinstance(op, ast.BitOr):
                return f"({lc} | {rc})", INT
            if isinstance(op, ast.BitXor):
                return f"({lc} ^ {rc})", INT
            if isinstance(op, ast.LShift):
                return (f"{{ let __a = {lc}; let __b = {rc}; if __b < 0 || __b > 62 {{ return Err(1); }} "
                        f"ck(__a.checked_mul(1i64 << __b))? }}"), INT
            return (f"{{ let __a = {lc}; let __b = {rc}; if __b < 0 {{ return Err(2); }} "
                    f"if __b > 63 {{ if __a < 0 {{ -1i64 }} else {{ 0i64 }} }} else {{ __a >> __b }} }}"), INT
        if isinstance(op, ast.Pow):
            if lt == INT and rt == INT:
                if isinstance(n.right, ast.Constant) and type(n.right.value) is int and 0 <= n.right.value < 2 ** 31:
                    return f"ck({lc}.checked_pow({n.right.value}u32))?", INT
                self.err(n, "int ** int needs a non-negative constant exponent (a negative exponent "
                            "would give a float); use float(x) ** y")
            a, b, _ = self.num_pair(n, lc, lt, rc, rt)
            return f"pow_f({a}, {b})?", FLOAT
        a, b, t = self.num_pair(n, lc, lt, rc, rt)
        if isinstance(op, (ast.Add, ast.Sub, ast.Mult)):
            s = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}[type(op)]
            if t == INT:
                meth = {"+": "checked_add", "-": "checked_sub", "*": "checked_mul"}[s]
                return f"ck({a}.{meth}({b}))?", INT
            return f"({a} {s} {b})", FLOAT
        if isinstance(op, ast.Div):
            return f"div_f(({a}) as f64, ({b}) as f64)?", FLOAT
        if isinstance(op, ast.FloorDiv):
            return (f"fdiv_i({a}, {b})?", INT) if t == INT else (f"fdiv_f({a}, {b})?", FLOAT)
        if isinstance(op, ast.Mod):
            return (f"mod_i({a}, {b})?", INT) if t == INT else (f"mod_f({a}, {b})?", FLOAT)
        self.err(n, f"unsupported operator {type(op).__name__}")

    def e_BoolOp(self, n):
        codes = []
        for v in n.values:
            c, t = self.ex(v)
            if t != BOOL:
                self.err(n, "`and`/`or` are only supported between bool expressions "
                            "(Python returns one of the operands otherwise)")
            codes.append(c)
        return "(" + (" && " if isinstance(n.op, ast.And) else " || ").join(codes) + ")", BOOL

    @staticmethod
    def _small_lit(n) -> bool:
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            n = n.operand
        return isinstance(n, ast.Constant) and type(n.value) is int and abs(n.value) < 2 ** 53

    def e_Compare(self, n):
        nodes = [n.left] + n.comparators
        items = [self.ex(x) for x in nodes]
        parts = []
        temps = []
        for i, (c, t) in enumerate(items):
            if t in ELEM:
                self.err(n, "comparing lists")
        for i, op in enumerate(n.ops):
            if type(op) not in _CMP:
                self.err(n, "`is`, `in` and similar comparisons are not supported")
            (lc, lt), (rc, rt) = items[i], items[i + 1]
            if lt != rt:
                if {lt, rt} == {INT, FLOAT} and self._small_lit(nodes[i] if lt == INT else nodes[i + 1]):
                    lc = f"({lc} as f64)" if lt == INT else lc
                    rc = f"({rc} as f64)" if rt == INT else rc
                else:
                    self.err(n, f"comparing {lt} with {rt} is not supported exactly "
                                f"(compare values of the same type)")
            items[i], items[i + 1] = (lc, lt), (rc, rt)
        if len(n.ops) == 1:
            return f"({items[0][0]} {_CMP[type(n.ops[0])]} {items[1][0]})", BOOL
        names = [self.fresh("c") for _ in items]
        lets = " ".join(f"let {nm} = {c};" for nm, (c, _) in zip(names, items))
        conds = " && ".join(f"{names[i]} {_CMP[type(op)]} {names[i + 1]}" for i, op in enumerate(n.ops))
        return f"{{ {lets} {conds} }}", BOOL

    def e_IfExp(self, n):
        cond = self.truth(n.test)
        a, at = self.ex(n.body)
        b, bt = self.ex(n.orelse)
        if at != bt or at not in SCALARS:
            self.err(n, "both branches of a conditional expression must have the same type")
        return f"(if {cond} {{ {a} }} else {{ {b} }})", at

    def e_Subscript(self, n):
        if not isinstance(n.value, ast.Name) or self.vars.get(n.value.id) not in ELEM:
            self.err(n, "subscripting is only supported on list variables")
        nm = n.value.id
        self.need_defined(nm, n)
        if isinstance(n.slice, ast.Slice):
            self.err(n, "slicing")
        ic, it = self.ex(n.slice)
        if it != INT:
            self.err(n, "list index must be int")
        return f"{nm}[ix({ic}, {nm}.len())?]", ELEM[self.vars[nm]]

    def e_Attribute(self, n):
        if isinstance(n.value, ast.Name):
            ok, mod = self.lookup_free(n.value.id)
            if n.value.id not in self.vars and ok and mod is _math:
                if n.attr in _MATH_CONST:
                    return _fmt_float(_MATH_CONST[n.attr]), FLOAT
                if n.attr == "inf":
                    return _fmt_float(float("inf")), FLOAT
        self.err(n, "attribute access is not supported")

    def e_Call(self, n):
        if n.keywords:
            self.err(n, "keyword arguments in calls")
        f = n.func
        if isinstance(f, ast.Name):
            nm = f.id
            if nm not in self.vars:
                ok, val = self.lookup_free(nm)
                callee = _as_jit(val) if ok else None
                if callee is not None:
                    return self.call_unit(n, callee)
                if ok and getattr(val, "__module__", None) == "math" and getattr(_math, nm, None) is val:
                    return self.math_call(n, nm)
                builtin = getattr(self, "b_" + nm, None)
                if builtin is not None and not ok:
                    return builtin(n)
                self.err(n, f"call to '{nm}' is not supported (only @cp.jit functions, math.* and a few builtins)")
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id not in self.vars:
            ok, mod = self.lookup_free(f.value.id)
            if ok and mod is _math:
                return self.math_call(n, f.attr)
        self.err(n, "unsupported call")

    def call_unit(self, n, jf):
        argc, argt = [], []
        for a in n.args:
            if isinstance(a, ast.Name) and self.vars.get(a.id) in ELEM:
                self.need_defined(a.id, a)
                argc.append(f"&{a.id}[..]")
                argt.append(self.vars[a.id])
            else:
                c, t = self.ex(a)
                if t in ELEM:
                    self.err(n, "pass lists to compiled functions as plain variables")
                argc.append(c)
                argt.append(t)
        argt = tuple(argt)
        if len(argt) != len(jf._params):
            self.err(n, "wrong number of arguments (defaults are not supported)")
        unit = self.crate.unit_for(jf, argt)
        self.unit.leaf = False
        return f"{unit.name}({', '.join(argc + ['__d + 1'])})?", unit.ret

    # builtins ---------------------------------------------------------------
    def b_abs(self, n):
        c, t = self.one(n)
        if t == INT:
            return f"ck({c}.checked_abs())?", INT
        if t == FLOAT:
            return f"({c}).abs()", FLOAT
        self.err(n, "abs() of non-number")

    def one(self, n):
        if len(n.args) != 1:
            self.err(n, "expected one argument")
        return self.ex(n.args[0])

    def _minmax(self, n, name):
        if len(n.args) < 2:
            self.err(n, f"{name}() with a single iterable is not supported")
        items = [self.ex(a) for a in n.args]
        t = items[0][1]
        if t not in (INT, FLOAT) or any(x[1] != t for x in items):
            self.err(n, f"{name}() needs arguments that are all int or all float")
        cur = items[0][0]
        cmp = "<" if name == "min" else ">"
        for c, _ in items[1:]:
            a, b = self.fresh("m"), self.fresh("m")
            cur = f"{{ let {a} = {cur}; let {b} = {c}; if {b} {cmp} {a} {{ {b} }} else {{ {a} }} }}"
        return cur, t

    def b_min(self, n):
        return self._minmax(n, "min")

    def b_max(self, n):
        return self._minmax(n, "max")

    def b_int(self, n):
        c, t = self.one(n)
        if t == INT:
            return c, INT
        if t == BOOL:
            return f"({c} as i64)", INT
        if t == FLOAT:
            return f"f2i(({c}).trunc())?", INT
        self.err(n, "int() argument")

    def b_float(self, n):
        c, t = self.one(n)
        if t == FLOAT:
            return c, FLOAT
        if t in (INT, BOOL):
            return f"({c} as f64)", FLOAT
        self.err(n, "float() argument")

    def b_bool(self, n):
        if len(n.args) != 1:
            self.err(n, "bool() needs one argument")
        return self.truth(n.args[0]), BOOL

    def b_len(self, n):
        a = n.args[0] if len(n.args) == 1 else None
        if isinstance(a, ast.Name) and self.vars.get(a.id) in ELEM:
            self.need_defined(a.id, a)
            return f"({a.id}.len() as i64)", INT
        self.err(n, "len() is only supported on list variables")

    def b_sum(self, n):
        a = n.args[0] if len(n.args) == 1 else None
        if isinstance(a, ast.Name) and self.vars.get(a.id) == LINT:
            self.need_defined(a.id, a)
            return f"sum_i(&{a.id}[..])?", INT
        self.err(n, "sum() is only supported on int lists (float sums use compensated "
                    "summation in CPython and would not match)")

    def math_call(self, n, fn):
        args = [self.ex(a) for a in n.args]

        def f64s():
            out = []
            for c, t in args:
                if t not in (INT, FLOAT):
                    self.err(n, f"math.{fn}() needs numbers")
                out.append(f"({c} as f64)" if t == INT else c)
            return out

        if fn in _MATH_FN1 and len(args) == 1:
            (x,) = f64s()
            v = self.fresh("x")
            return (f"{{ let {v}: f64 = {x}; mc({v}.{_MATH_FN1[fn]}(), {v}.is_nan(), {v}.is_finite())? }}"), FLOAT
        if fn == "log" and len(args) == 1:
            (x,) = f64s()
            v = self.fresh("x")
            return (f"{{ let {v}: f64 = {x}; if {v} <= 0.0 {{ return Err(2); }} "
                    f"mc({v}.ln(), {v}.is_nan(), {v}.is_finite())? }}"), FLOAT
        if fn == "fabs" and len(args) == 1:
            return f"({f64s()[0]}).abs()", FLOAT
        if fn in ("floor", "ceil") and len(args) == 1:
            if args[0][1] == INT:
                return args[0][0], INT
            return f"f2i(({f64s()[0]}).{fn}())?", INT
        if fn == "atan2" and len(args) == 2:
            a, b = f64s()
            return f"({a}).atan2({b})", FLOAT
        if fn == "hypot" and len(args) == 2:
            a, b = f64s()
            x, y = self.fresh("x"), self.fresh("y")
            return (f"{{ let {x}: f64 = {a}; let {y}: f64 = {b}; mc({x}.hypot({y}), {x}.is_nan() || {y}.is_nan(), "
                    f"{x}.is_finite() && {y}.is_finite())? }}"), FLOAT
        if fn == "isnan" and len(args) == 1:
            return f"({f64s()[0]}).is_nan()", BOOL
        if fn == "isinf" and len(args) == 1:
            return f"({f64s()[0]}).is_infinite()", BOOL
        self.err(n, f"math.{fn}() is not supported")


# ─────────────────────────────────────────────────────────────────────────────
# Build + load
# ─────────────────────────────────────────────────────────────────────────────
def cache_dir() -> str:
    d = os.environ.get("COPPERHEAD_CACHE")
    if not d:
        base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
        base = base or os.path.join(os.path.expanduser("~"), ".cache")
        d = os.path.join(base, "copperhead")
    os.makedirs(d, exist_ok=True)
    return d


def _find_rustc() -> Optional[str]:
    p = os.environ.get("RUSTC") or shutil.which("rustc")
    if p:
        return p
    cand = os.path.join(os.path.expanduser("~"), ".cargo", "bin", "rustc" + (".exe" if os.name == "nt" else ""))
    return cand if os.path.exists(cand) else None


def rust_available() -> bool:
    return _find_rustc() is not None


_RUSTC_VERSION: Optional[str] = None


def _rustc_version(rustc: str) -> str:
    global _RUSTC_VERSION
    if _RUSTC_VERSION is None:
        try:
            _RUSTC_VERSION = subprocess.run([rustc, "-vV"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout
        except Exception:
            _RUSTC_VERSION = "unknown"
    return _RUSTC_VERSION


def _lib_ext() -> str:
    return ".dll" if sys.platform == "win32" else ".dylib" if sys.platform == "darwin" else ".so"


def clear_cache() -> None:
    d = cache_dir()
    for f in os.listdir(d):
        if f.startswith("cp_"):
            try:
                os.remove(os.path.join(d, f))
            except OSError:
                pass


def build_library(rust_src: str) -> str:
    """Compile Rust source to a shared library (content-hash cached). Returns its path."""
    rustc = _find_rustc()
    if not rustc:
        raise BuildError("rustc not found - install Rust from https://rustup.rs to enable compilation")
    flags = ["-C", "opt-level=3", "-C", "panic=abort", "-C", "debuginfo=0", "--edition", "2021"]
    h = hashlib.sha256((rust_src + _rustc_version(rustc) + " ".join(flags)).encode()).hexdigest()[:24]
    d = cache_dir()
    out = os.path.join(d, f"cp_{h}{_lib_ext()}")
    if os.path.exists(out):
        return out
    src = os.path.join(d, f"cp_{h}.rs")
    with open(src, "w", encoding="utf-8") as f:
        f.write(rust_src)
    tmp = os.path.join(d, f"cp_tmp{os.getpid()}_{threading.get_ident()}_{h}{_lib_ext()}")
    r = subprocess.run([rustc, "--crate-type", "cdylib", *flags, "-o", tmp, src],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0:
        raise BuildError("rustc failed:\n" + r.stderr[-3000:])
    try:
        os.replace(tmp, out)
    except OSError:
        if not os.path.exists(out):
            raise
    for extra in (tmp + ".lib", tmp + ".exp", tmp[:-len(_lib_ext())] + ".pdb", tmp + ".pdb"):
        try:
            os.remove(extra)
        except OSError:
            pass
    return out


_CTYPE = {INT: ctypes.c_int64, FLOAT: ctypes.c_double, BOOL: ctypes.c_bool}


def _classify(v) -> Optional[str]:
    t = type(v)
    if t is bool:
        return BOOL
    if t is int:
        return INT if MIN_I64 <= v <= MAX_I64 else None
    if t is float:
        return FLOAT
    if t is list:
        if not v:
            return None
        kinds = set(map(type, v))
        if kinds <= {int, bool}:
            return LINT
        if kinds == {float}:
            return LFLT
        return None
    if t is array.array:
        return LINT if v.typecode == "q" else LFLT if v.typecode == "d" else None
    dt = getattr(v, "dtype", None)
    if dt is not None and getattr(v, "ndim", 0) == 1 and getattr(v, "flags", None) is not None \
            and v.flags["C_CONTIGUOUS"]:
        if str(dt) == "int64":
            return LINT
        if str(dt) == "float64":
            return LFLT
    return None


def _to_buffer(v, t):
    """Returns (pointer, length, keepalive)."""
    if type(v) is list:
        a = array.array("q" if t == LINT else "d", v)
        p, n = a.buffer_info()
        return p, n, a
    if type(v) is array.array:
        p, n = v.buffer_info()
        return p, n, v
    return v.ctypes.data, v.shape[0], v


class _Spec:
    """A compiled specialisation ready to call."""

    def __init__(self, lib_path, argtypes, ret, guards, rust_src):
        self.lib = ctypes.CDLL(lib_path)  # CDLL => GIL released while Rust runs
        self.argtypes = argtypes
        self.ret = ret
        self.guards = guards
        self.rust_src = rust_src
        fn = self.lib.cp_entry
        at = []
        for t in argtypes:
            if t in SCALARS:
                at.append(_CTYPE[t])
            else:
                at += [ctypes.c_void_p, ctypes.c_size_t]
        at.append(ctypes.POINTER(ctypes.c_int32))
        fn.argtypes = at
        fn.restype = _CTYPE[ret]
        self.fn = fn

    def call(self, args):
        for name, val, pyfn in self.guards:
            found, cur = _free_lookup(pyfn, name)
            if not found or cur != val or type(cur) is not type(val):
                return _FALLBACK
        flat = []
        keep = []
        for a, t in zip(args, self.argtypes):
            if t in SCALARS:
                flat.append(a)
            else:
                p, n, k = _to_buffer(a, t)
                flat += [p, n]
                keep.append(k)
        err = ctypes.c_int32(0)
        r = self.fn(*flat, ctypes.byref(err))
        if err.value:
            return _FALLBACK
        return r


_FALLBACK = object()
_LOCK = threading.RLock()


def _build_rust(jf: "JitFunction", argtypes: Tuple[str, ...]):
    crate = _Crate()
    root = crate.unit_for(jf, argtypes)
    parts = [PRELUDE]
    for u in crate.units.values():
        parts.append(u.code)
    sig, call = [], []
    for i, t in enumerate(argtypes):
        if t in SCALARS:
            sig.append(f"a{i}: {RS[t]}")
            call.append(f"a{i}")
        else:
            e = RS[ELEM[t]]
            sig.append(f"p{i}: *const {e}, n{i}: usize")
            call.append(f"unsafe {{ std::slice::from_raw_parts(if n{i} == 0 {{ std::ptr::NonNull::<{e}>::dangling().as_ptr() }} else {{ p{i} }}, n{i}) }}")
    sig.append("err: *mut i32")
    ret = RS[root.ret]
    parts.append(
        f'#[no_mangle]\npub extern "C" fn cp_entry({", ".join(sig)}) -> {ret} {{\n'
        f'    match {root.name}({", ".join(call + ["0"])}) {{\n'
        f'        Ok(v) => v,\n'
        f'        Err(e) => {{ unsafe {{ *err = e; }} Default::default() }}\n'
        f'    }}\n}}\n')
    return "\n".join(parts), root, crate


# ─────────────────────────────────────────────────────────────────────────────
# Public decorator
# ─────────────────────────────────────────────────────────────────────────────
def _verbose() -> bool:
    return os.environ.get("COPPERHEAD_VERBOSE", "") not in ("", "0")


_REGISTRY: Dict[int, "JitFunction"] = {}


def _as_jit(val) -> Optional["JitFunction"]:
    """Map a callee object to its JitFunction: a decorated function, the plain function behind one
    (e.g. a recursive name when written ``jit(f)``), or any other plain Python function (compiled
    automatically as part of the same crate)."""
    if isinstance(val, JitFunction):
        return val
    if isinstance(val, types.FunctionType):
        jf = _REGISTRY.get(id(val))
        if jf is None:
            jf = JitFunction(val, warn=False)
        return jf
    return None


class JitFunction:
    """Callable wrapper: native Rust when possible, original Python otherwise."""

    def __init__(self, func: Callable, strict: bool = False, no_gil: bool = False,
                 warn: bool = True, eager: bool = False):
        functools.update_wrapper(self, func)
        self._py = func
        _REGISTRY[id(func)] = self
        self._strict = strict
        self._warn = warn
        self._no_gil = no_gil
        self._specs: Dict[Tuple[str, ...], Any] = {}
        self._reasons: Dict[Tuple[str, ...], str] = {}
        self._warned = False
        self._tree = None
        self._line_offset = 0
        self._params: List[str] = []
        self._disabled = os.environ.get("COPPERHEAD_DISABLE", "") not in ("", "0")
        self._copperhead_compile = True
        self._copperhead_no_gil = no_gil
        self.native_calls = 0
        self.python_calls = 0
        try:
            src = textwrap.dedent(inspect.getsource(func))
            mod = ast.parse(src)
            fd = next(n for n in ast.walk(mod) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            if isinstance(fd, ast.AsyncFunctionDef):
                raise Unsupported("async functions")
            if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(fd)):
                raise Unsupported("generators")
            self._tree = fd
            self._line_offset = func.__code__.co_firstlineno - 1
            self._params = [a.arg for a in fd.args.posonlyargs + fd.args.args]
        except Unsupported as e:
            self._reasons[()] = str(e)
            self._tree = None
        except (OSError, TypeError, StopIteration, SyntaxError) as e:
            self._reasons[()] = f"source code not available ({type(e).__name__})"
            self._tree = None
        if eager and self._tree is not None:
            at = [_ann_to_type(func.__annotations__.get(p)) for p in self._params]
            if all(at):
                self._get_spec(tuple(at))

    # -- introspection --
    def __repr__(self):
        return f"<cp.jit {self.__name__}: {len(self._specs)} specialisation(s)>"

    def __get__(self, obj, objtype=None):
        return self if obj is None else functools.partial(self.__call__, obj)

    @property
    def py_func(self):
        """The original, uncompiled Python function."""
        return self._py

    def rust_source(self, *args) -> str:
        """The Rust that would be generated for these example arguments."""
        at = self._types_of(args)
        if at is None:
            raise Unsupported("unsupported argument types")
        if self._tree is None:
            raise Unsupported(self._reasons.get((), "no source"))
        src, _, _ = _build_rust(self, at)
        return src

    def explain(self, *args) -> str:
        """Why is this (not) compiled for these arguments?"""
        at = self._types_of(args)
        if at is None:
            return "arguments are not int/float/bool/non-empty list[int|float]: runs in Python"
        spec = self._get_spec(at)
        if spec is not None:
            return f"compiled to Rust ({', '.join(at)})"
        return "runs in Python: " + self._reasons.get(at, self._reasons.get((), "unknown"))

    # -- machinery --
    def _types_of(self, args) -> Optional[Tuple[str, ...]]:
        out = []
        for a in args:
            t = _classify(a)
            if t is None:
                return None
            out.append(t)
        return tuple(out)

    def _get_spec(self, at: Tuple[str, ...]):
        if at in self._specs:
            return self._specs[at]
        with _LOCK:
            if at in self._specs:
                return self._specs[at]
            spec = None
            try:
                if self._tree is None:
                    raise Unsupported(self._reasons.get((), "source not available"))
                src, root, crate = _build_rust(self, at)
                lib = build_library(src)
                spec = _Spec(lib, at, root.ret, list(crate.guards), src)
            except (Unsupported, BuildError, OSError) as e:
                self._reasons[at] = str(e)
                if self._strict:
                    raise
                if self._warn and not self._warned:
                    self._warned = True
                    warnings.warn(f"copperhead: '{self.__name__}' runs as plain Python: {e}",
                                  CopperheadWarning, stacklevel=4)
            self._specs[at] = spec
            return spec

    def __call__(self, *args, **kwargs):
        if kwargs or self._disabled or len(args) != len(self._params):
            self.python_calls += 1
            return self._py(*args, **kwargs)
        at = self._types_of(args)
        spec = self._get_spec(at) if at is not None else None
        if spec is not None:
            try:
                r = spec.call(args)
            except (OverflowError, TypeError, ValueError, ctypes.ArgumentError):
                r = _FALLBACK
            if r is not _FALLBACK:
                self.native_calls += 1
                return r
        self.python_calls += 1
        return self._py(*args)


def jit(func=None, *, strict: bool = False, no_gil: bool = False, warn: bool = True, eager: bool = False):
    """Compile a Python function to native Rust on first call.

    Usage: ``@cp.jit``  or  ``@cp.jit(strict=True)``.
      strict  raise instead of silently falling back to Python
      warn    emit one CopperheadWarning explaining a fallback (default True)
      eager   compile at decoration time when all parameters are annotated
    """
    def wrap(f):
        return JitFunction(f, strict=strict, no_gil=no_gil, warn=warn, eager=eager)
    return wrap(func) if callable(func) else wrap
