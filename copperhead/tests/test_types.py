"""
Tests for Copperhead type system.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copperhead as cp


class TestPrimitiveTypes:
    """Test primitive type mappings."""
    
    def test_f32_type(self):
        """Test f32 type."""
        assert cp.f32 is float
    
    def test_f64_type(self):
        """Test f64 type."""
        assert cp.f64 is float
    
    def test_i8_type(self):
        """Test i8 type."""
        assert cp.i8 is int
    
    def test_i16_type(self):
        """Test i16 type."""
        assert cp.i16 is int
    
    def test_i32_type(self):
        """Test i32 type."""
        assert cp.i32 is int
    
    def test_i64_type(self):
        """Test i64 type."""
        assert cp.i64 is int
    
    def test_u8_type(self):
        """Test u8 type."""
        assert cp.u8 is int
    
    def test_u16_type(self):
        """Test u16 type."""
        assert cp.u16 is int
    
    def test_u32_type(self):
        """Test u32 type."""
        assert cp.u32 is int
    
    def test_u64_type(self):
        """Test u64 type."""
        assert cp.u64 is int
    
    def test_usize_type(self):
        """Test usize type."""
        assert cp.usize is int
    
    def test_isize_type(self):
        """Test isize type."""
        assert cp.isize is int
    
    def test_bool_type(self):
        """Test bool type."""
        assert cp.bool is bool
    
    def test_str_type(self):
        """Test str type."""
        assert cp.str is str
    
    def test_bytes_type(self):
        """Test bytes type."""
        assert cp.bytes is bytes
    
    def test_char_type(self):
        """Test char type."""
        assert cp.char is str


class TestOwnershipTypes:
    """Test ownership and borrowing types."""
    
    def test_mut_reference(self):
        """Test mutable reference type."""
        state = {"value": 42}
        mut_ref = cp.mut(state)
        assert mut_ref.value == state
    
    def test_ref_reference(self):
        """Test immutable reference type."""
        data = [1, 2, 3]
        immut_ref = cp.ref(data)
        assert immut_ref.value == data
    
    def test_mut_class_getitem(self):
        """Test mut class getitem."""
        result = cp.mut[int]
        assert result is cp.MutRef
    
    def test_ref_class_getitem(self):
        """Test ref class getitem."""
        result = cp.ref[int]
        assert result is cp.ImmutRef


class TestCollectionTypes:
    """Test collection types."""
    
    def test_vec_creation(self):
        """Test Vec creation."""
        vec = cp.Vec([1, 2, 3])
        assert len(vec) == 3
        assert vec[0] == 1
        assert vec[1] == 2
        assert vec[2] == 3
    
    def test_vec_push(self):
        """Test Vec push."""
        vec = cp.Vec()
        vec.push(1)
        vec.push(2)
        assert len(vec) == 2
        assert vec[0] == 1
        assert vec[1] == 2
    
    def test_vec_pop(self):
        """Test Vec pop."""
        vec = cp.Vec([1, 2, 3])
        val = vec.pop()
        assert val == 3
        assert len(vec) == 2
    
    def test_vec_len(self):
        """Test Vec len."""
        vec = cp.Vec([1, 2, 3, 4, 5])
        assert vec.len() == 5
    
    def test_vec_is_empty(self):
        """Test Vec is_empty."""
        vec = cp.Vec()
        assert vec.is_empty() is True
        vec.push(1)
        assert vec.is_empty() is False
    
    def test_vec_get(self):
        """Test Vec get."""
        vec = cp.Vec([10, 20, 30])
        assert vec.get(0) == 10
        assert vec.get(1) == 20
        assert vec.get(2) == 30
    
    def test_vec_get_out_of_bounds(self):
        """Test Vec get out of bounds."""
        vec = cp.Vec([1, 2, 3])
        with pytest.raises(IndexError):
            vec.get(5)
    
    def test_vec_setitem(self):
        """Test Vec setitem."""
        vec = cp.Vec([1, 2, 3])
        vec[1] = 20
        assert vec[1] == 20
    
    def test_vec_setitem_out_of_bounds(self):
        """Test Vec setitem out of bounds."""
        vec = cp.Vec([1, 2, 3])
        with pytest.raises(IndexError):
            vec[5] = 10
    
    def test_vec_iter(self):
        """Test Vec iteration."""
        vec = cp.Vec([1, 2, 3])
        result = list(vec)
        assert result == [1, 2, 3]
    
    def test_hashmap_creation(self):
        """Test HashMap creation."""
        hashmap = cp.HashMap({"a": 1, "b": 2})
        assert hashmap.len() == 2
        assert hashmap["a"] == 1
        assert hashmap["b"] == 2
    
    def test_hashmap_insert(self):
        """Test HashMap insert."""
        hashmap = cp.HashMap()
        hashmap.insert("x", 10)
        hashmap.insert("y", 20)
        assert hashmap.len() == 2
        assert hashmap["x"] == 10
        assert hashmap["y"] == 20
    
    def test_hashmap_get(self):
        """Test HashMap get."""
        hashmap = cp.HashMap({"key": "value"})
        assert hashmap.get("key") == "value"
        assert hashmap.get("missing") is None
    
    def test_hashmap_remove(self):
        """Test HashMap remove."""
        hashmap = cp.HashMap({"a": 1, "b": 2})
        val = hashmap.remove("a")
        assert val == 1
        assert hashmap.len() == 1
        assert hashmap.get("a") is None
    
    def test_hashmap_contains_key(self):
        """Test HashMap contains_key."""
        hashmap = cp.HashMap({"x": 1})
        assert hashmap.contains_key("x") is True
        assert hashmap.contains_key("y") is False
    
    def test_hashmap_keys(self):
        """Test HashMap keys."""
        hashmap = cp.HashMap({"a": 1, "b": 2})
        keys = hashmap.keys()
        assert set(keys) == {"a", "b"}
    
    def test_hashmap_values(self):
        """Test HashMap values."""
        hashmap = cp.HashMap({"a": 1, "b": 2})
        values = hashmap.values()
        assert set(values) == {1, 2}
    
    def test_hashmap_items(self):
        """Test HashMap items."""
        hashmap = cp.HashMap({"a": 1, "b": 2})
        items = hashmap.items()
        assert set(items) == {("a", 1), ("b", 2)}
    
    def test_hashmap_setitem(self):
        """Test HashMap setitem."""
        hashmap = cp.HashMap()
        hashmap["key"] = "value"
        assert hashmap["key"] == "value"
    
    def test_hashmap_contains(self):
        """Test HashMap contains."""
        hashmap = cp.HashMap({"x": 1})
        assert "x" in hashmap
        assert "y" not in hashmap


class TestOptionType:
    """Test Option type."""
    
    def test_option_some(self):
        """Test Option with value."""
        opt = cp.Option(42)
        assert opt.is_some() is True
        assert opt.is_none() is False
        assert opt.unwrap() == 42
    
    def test_option_none(self):
        """Test Option without value."""
        opt = cp.Option()
        assert opt.is_some() is False
        assert opt.is_none() is True
    
    def test_option_unwrap_none(self):
        """Test Option unwrap on None."""
        opt = cp.Option()
        with pytest.raises(ValueError):
            opt.unwrap()
    
    def test_option_unwrap_or(self):
        """Test Option unwrap_or."""
        opt_some = cp.Option(42)
        opt_none = cp.Option()
        
        assert opt_some.unwrap_or(0) == 42
        assert opt_none.unwrap_or(0) == 0
    
    def test_option_map(self):
        """Test Option map."""
        opt = cp.Option(5)
        mapped = opt.map(lambda x: x * 2)
        assert mapped.unwrap() == 10
        
        opt_none = cp.Option()
        mapped_none = opt_none.map(lambda x: x * 2)
        assert mapped_none.is_none()


class TestResultType:
    """Test Result type."""
    
    def test_result_ok(self):
        """Test Result with value."""
        result = cp.Ok(42)
        assert result.is_ok() is True
        assert result.is_err() is False
        assert result.unwrap() == 42
    
    def test_result_err(self):
        """Test Result with error."""
        result = cp.Err("something went wrong")
        assert result.is_ok() is False
        assert result.is_err() is True
    
    def test_result_unwrap_err(self):
        """Test Result unwrap on error."""
        result = cp.Err("error")
        with pytest.raises(RuntimeError):
            result.unwrap()
    
    def test_result_unwrap_or(self):
        """Test Result unwrap_or."""
        ok_result = cp.Ok(42)
        err_result = cp.Err("error")
        
        assert ok_result.unwrap_or(0) == 42
        assert err_result.unwrap_or(0) == 0
    
    def test_result_map(self):
        """Test Result map."""
        ok_result = cp.Ok(5)
        mapped = ok_result.map(lambda x: x * 2)
        assert mapped.unwrap() == 10
        
        err_result = cp.Err("error")
        mapped_err = err_result.map(lambda x: x * 2)
        assert mapped_err.is_err()


class TestMathModule:
    """Test Math module."""
    
    def test_sin(self):
        """Test sin function."""
        import math
        result = cp.math.sin(math.pi / 2)
        assert abs(result - 1.0) < 1e-10
    
    def test_cos(self):
        """Test cos function."""
        import math
        result = cp.math.cos(0)
        assert abs(result - 1.0) < 1e-10
    
    def test_tan(self):
        """Test tan function."""
        import math
        result = cp.math.tan(0)
        assert abs(result - 0.0) < 1e-10
    
    def test_sqrt(self):
        """Test sqrt function."""
        result = cp.math.sqrt(4)
        assert abs(result - 2.0) < 1e-10
    
    def test_pow(self):
        """Test pow function."""
        result = cp.math.pow(2, 3)
        assert abs(result - 8.0) < 1e-10
    
    def test_abs(self):
        """Test abs function."""
        assert cp.math.abs(-5) == 5
        assert cp.math.abs(5) == 5
    
    def test_floor(self):
        """Test floor function."""
        assert cp.math.floor(3.7) == 3
        assert cp.math.floor(3.2) == 3
    
    def test_ceil(self):
        """Test ceil function."""
        assert cp.math.ceil(3.2) == 4
        assert cp.math.ceil(3.7) == 4
    
    def test_log(self):
        """Test log function."""
        import math
        result = cp.math.log(math.e)
        assert abs(result - 1.0) < 1e-10
    
    def test_log2(self):
        """Test log2 function."""
        result = cp.math.log2(8)
        assert abs(result - 3.0) < 1e-10
    
    def test_log10(self):
        """Test log10 function."""
        result = cp.math.log10(100)
        assert abs(result - 2.0) < 1e-10
    
    def test_min(self):
        """Test min function."""
        assert cp.math.min(5, 3) == 3
        assert cp.math.min(3, 5) == 3
    
    def test_max(self):
        """Test max function."""
        assert cp.math.max(5, 3) == 5
        assert cp.math.max(3, 5) == 5


class TestDecorators:
    """Test decorators."""
    
    def test_compile_decorator(self):
        """Test @cp.compile decorator."""
        @cp.compile(target="rust")
        def my_function(x: cp.f64) -> cp.f64:
            return x * 2
        
        assert hasattr(my_function, '_copperhead_target')
        assert my_function._copperhead_target == "rust"
        assert hasattr(my_function, '_copperhead_compile')
        assert my_function._copperhead_compile is True
    
    def test_no_gil_decorator(self):
        """Test @cp.no_gil decorator."""
        @cp.no_gil
        def my_function(x: cp.f64) -> cp.f64:
            return x * 2
        
        assert hasattr(my_function, '_copperhead_no_gil')
        assert my_function._copperhead_no_gil is True


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_sizeof(self):
        """Test sizeof function."""
        assert cp.sizeof(42) > 0
        assert cp.sizeof("hello") > 0
        assert cp.sizeof([1, 2, 3]) > 0
    
    def test_type_name(self):
        """Test type_name function."""
        assert cp.type_name(42) == "int"
        assert cp.type_name("hello") == "str"
        assert cp.type_name([1, 2]) == "list"
    
    def test_assert_type(self):
        """Test assert_type function."""
        cp.assert_type(42, int)
        cp.assert_type("hello", str)
        cp.assert_type([1, 2], list)
        
        with pytest.raises(TypeError):
            cp.assert_type(42, str)
        
        with pytest.raises(TypeError):
            cp.assert_type("hello", int)
