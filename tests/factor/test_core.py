"""Tests for factor.core module."""

import pytest

from factor.core import (
    FIELD,
    FORMAT,
    INDEX,
    TIMETYPE,
    BasicFactor,
    DelayedFunction,
    delay,
    fn_params,
)


class DummyFactor(BasicFactor):
    """Concrete implementation of BasicFactor for testing."""

    def shift(self, n: int = 1):
        new_fac = DummyFactor(
            *self._depends, fn=self.fn, name=self.name, insert_time=self.insert_time
        )
        new_fac.lag = self.lag + n
        return new_fac


def dummy_fn(date, cb=None, x=1):
    """Test function for BasicFactor."""
    return x + 1


def fn_with_defaults(date, cb=None, x=1, y=2):
    """Test function with default arguments."""
    return x + y


class TestDelayedFunction:
    """Tests for DelayedFunction class."""

    def test_delay_basic(self):
        """Test delay() wraps a function."""
        d = delay(lambda x: x + 1)
        assert isinstance(d, DelayedFunction)
        assert d.func is not None

    def test_delayed_function_call(self):
        """Test calling a delayed function."""
        d = delay(lambda x, y=1: x + y)
        result = d(5)
        assert result == 6

    def test_delayed_function_with_stored_kwargs(self):
        """Test delayed function with stored kwargs."""

        def add_fn(x, y=1):
            return x + y

        d = DelayedFunction(add_fn, stored_kwargs={"y": 10})
        result = d(5)
        assert result == 15

    def test_delayed_function_bind(self):
        """Test binding new kwargs."""

        def add_fn(x, y=1):
            return x + y

        d = delay(add_fn)
        bound = d.bind(y=10)
        assert isinstance(bound, DelayedFunction)
        result = bound(5)
        assert result == 15

    def test_delayed_function_override_bind(self):
        """Test that bind merges kwargs correctly."""

        def add_fn(x, y=1, z=3):
            return x + y + z

        d = DelayedFunction(add_fn, stored_kwargs={"y": 10})
        bound = d.bind(z=5)
        result = bound(1)
        assert result == 16  # 1 + 10 + 5

    def test_delayed_function_name(self):
        """Test __name__ property."""

        def my_test_fn():
            pass

        d = delay(my_test_fn)
        assert d.__name__ == "my_test_fn"

    def test_fn_params_basic(self):
        """Test fn_params extracts parameters."""
        params = fn_params(lambda x, y, z=1: None)
        assert ("z", 1) in params

    def test_fn_params_with_defaults(self):
        """Test fn_params with default values."""
        params = fn_params(fn_with_defaults)
        assert ("x", 1) in params
        assert ("y", 2) in params


class TestBasicFactor:
    """Tests for BasicFactor class."""

    def test_basic_factor_creation(self):
        """Test creating a basic factor."""
        fac = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        assert fac.name == "test"
        assert fac.fn is not None
        assert fac.insert_time == "15:00:00"
        assert fac.lag == 0

    def test_basic_factor_name_from_fn(self):
        """Test factor name defaults to function name."""
        fac = DummyFactor(fn=dummy_fn, insert_time="15:00:00")
        assert fac.name == "dummy_fn"

    def test_basic_factor_version(self):
        """Test version is computed."""
        fac = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        assert fac.version is not None
        assert len(fac.version) == 32  # MD5 hex length

    def test_basic_factor_depends(self):
        """Test factor with dependencies."""
        dep = DummyFactor(fn=dummy_fn, name="dep", insert_time="15:00:00")
        fac = DummyFactor(dep, fn=dummy_fn, name="parent", insert_time="15:00:00")
        assert len(fac._depends) == 1
        assert fac._depends[0] is dep

    def test_basic_factor_circular_detection(self):
        """Test circular dependency raises error."""
        fac1 = DummyFactor(fn=dummy_fn, name="fac1", insert_time="15:00:00")
        fac2 = DummyFactor(fac1, fn=dummy_fn, name="fac2", insert_time="15:00:00")
        fac1._depends = [fac2]  # Create cycle
        with pytest.raises(ValueError, match="Circular dependency"):
            DummyFactor(fac2, fn=dummy_fn, name="circular", insert_time="15:00:00")

    def test_basic_factor_get_dependencies(self):
        """Test get_dependencies returns direct deps."""
        dep = DummyFactor(fn=dummy_fn, name="dep", insert_time="15:00:00")
        fac = DummyFactor(dep, fn=dummy_fn, name="parent", insert_time="15:00:00")
        assert fac.get_dependencies() == [dep]

    def test_basic_factor_get_all_dependencies(self):
        """Test get_all_dependencies returns transitive deps."""
        dep1 = DummyFactor(fn=dummy_fn, name="dep1", insert_time="15:00:00")
        dep2 = DummyFactor(fn=dummy_fn, name="dep2", insert_time="15:00:00")
        fac = DummyFactor(
            dep1, dep2, fn=dummy_fn, name="parent", insert_time="15:00:00"
        )
        all_deps = fac.get_all_dependencies()
        assert dep1 in all_deps
        assert dep2 in all_deps

    def test_basic_factor_version_with_depends(self):
        """Test version changes with dependency changes."""

        def fn1(date, cb=None):
            return 1

        def fn2(date, cb=None):
            return 2

        fac_with_fn1 = DummyFactor(fn=fn1, name="fac", insert_time="15:00:00")
        fac_with_fn2 = DummyFactor(fn=fn2, name="fac", insert_time="15:00:00")

        # Different function implementations should produce different versions
        assert fac_with_fn1.version != fac_with_fn2.version

    def test_basic_factor_same_version_for_same_code(self):
        """Test same code produces same version."""
        fac1 = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        fac2 = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        assert fac1.version == fac2.version

    def test_basic_factor_tb_name(self):
        """Test tb_name path generation."""
        fac = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        assert fac.tb_name.startswith("factors/name=test/version=")

    def test_basic_factor_str(self):
        """Test __str__ returns name."""
        fac = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        assert str(fac) == "test"

    def test_basic_factor_repr(self):
        """Test __repr__ contains function path and name."""
        fac = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        repr_str = repr(fac)
        assert "dummy_fn" in repr_str
        assert "test" in repr_str

    def test_basic_factor_shift(self):
        """Test shift updates lag."""
        fac = DummyFactor(fn=dummy_fn, name="test", insert_time="15:00:00")
        shifted = fac.shift(5)
        assert shifted.lag == 5


class TestConstants:
    """Tests for constants."""

    def test_field_constants(self):
        """Test FIELD class constants."""
        assert FIELD.DATE == "date"
        assert FIELD.TIME == "time"
        assert FIELD.DATETIME == "datetime"
        assert FIELD.ASSET == "asset"
        assert FIELD.VALUE == "value"
        assert FIELD.VERSION == "version"
        assert FIELD.NAME == "name"
        assert FIELD.FIELDNAMES == "field_names"

    def test_index_tuple(self):
        """Test INDEX contains ASSET and DATETIME."""
        assert INDEX == (FIELD.ASSET, FIELD.DATETIME)

    def test_timetype_enum(self):
        """Test TIMETYPE enum values."""
        assert TIMETYPE.FIXED.value == "fixed_time"
        assert TIMETYPE.REAL.value == "real_time"

    def test_format_constants(self):
        """Test FORMAT class constants."""
        assert FORMAT.DATE == "%Y-%m-%d"
        assert FORMAT.TIME == "%H:%M:%S"
