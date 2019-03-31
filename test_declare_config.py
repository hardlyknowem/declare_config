"""Test cases for declare_config.py."""
import os
import pathlib
import tempfile

import pytest
import yaml

from declare_config import Configuration, Setting, configuration_provider, \
        enable_expanduser, enable_nested_settings


# ============================================================================
# Setting tests
# ============================================================================

def test_configured_value_simple():
    class TestClass(Configuration):
        test_value = Setting('x')

    foo = TestClass({"x": "bar"})
    assert foo.test_value == "bar"


def test_configured_value_type():
    class TestClass(Configuration):
        test_value = Setting('x', setting_type=int)

    foo = TestClass({"x": "1"})
    assert foo.test_value == 1


def test_no_config_given():
    class TestClass(Configuration):
        x = Setting("path.to.config")

    foo = TestClass()
    with pytest.raises(ValueError) as err:
        print(foo.x)

    assert "missing required config path.to.config" in str(err)


def test_configured_value_default():
    class TestClass(Configuration):
        test_value = Setting('x', 5000, int)

    foo = TestClass()
    assert foo.test_value == 5000

    foo = TestClass({"x": "10000"})
    assert foo.test_value == 10000


def test_require_default():
    with pytest.raises(ValueError) as err:
        Setting(config_path=None, default=None)

    assert "must provide config_path or default" in str(err)


def test_require_callable_type():
    with pytest.raises(ValueError) as err:
        Setting("x", setting_type="not_callable")

    assert "must provide callable for setting_type" in str(err)


def test_configured_value_class_ref():
    my_field = Setting('x', 5000, int)

    class TestClass(Configuration):
        test_value = my_field

    assert TestClass.test_value == my_field


def test_no_config_path():
    class TestClass(Configuration):
        test_value = Setting(None, "/usr/var/log")

    foo = TestClass({})
    assert foo.test_value == "/usr/var/log"


def test_nested_path():
    class TestClass(Configuration):
        test_value = Setting("a.b.c.d", setting_type=int)

    foo = TestClass({"a": {"b": {"c": {"d": "5"}}}})
    assert foo.test_value == 5


# ============================================================================
# Preprocessor/Postprocessor tests
# ============================================================================

def test_expanduser():
    @enable_expanduser
    class TestClass(Configuration):
        x = Setting("x", setting_type=pathlib.Path)
        y = Setting("y", setting_type=pathlib.Path)
        z = Setting("z", setting_type=int)

    foo = TestClass({"x": "~/file.txt", "y": "/usr/lib/file.txt", "z": "3"})
    assert foo.x == pathlib.Path("~/file.txt").expanduser()
    assert foo.y == pathlib.Path("/usr/lib/file.txt")
    assert foo.z == 3


def test_nested_settings():
    @enable_nested_settings
    class TestClass(Configuration):
        a = Setting("a", "foo")
        b = Setting("b", "${a}bar")
        c = Setting("c", "${b}baz")
        d = Setting("d", "/usr/tmp/${c}")

    foo = TestClass({"d": "/usr/tmp/log/${c}"})
    assert foo.a == "foo"
    assert foo.b == "foobar"
    assert foo.c == "foobarbaz"
    assert foo.d == "/usr/tmp/log/foobarbaz"


# ============================================================================
# Provider tests
# ============================================================================

def test_load_requires_provider():
    class TestClass(Configuration):
        pass

    with pytest.raises(TypeError) as err:
        TestClass.load()

    assert "TestClass has no provider defined" in str(err)


def test_provider():
    @configuration_provider({"x": "a"})
    class TestClass(Configuration):
        x = Setting("x", "foo")

    foo = TestClass.load()
    assert foo.x == "a"


def test_file_provider():
    temp = tempfile.NamedTemporaryFile('w')

    @configuration_provider(temp.name)
    class TestClass(Configuration):
        x = Setting("x", 4, setting_type=int)

    with temp as fp:
        fp.write(yaml.dump({"x": "5"}))
        fp.flush()
        foo = TestClass.load()
        assert foo.x == 5


def test_must_exist():
    temp = tempfile.NamedTemporaryFile('w')

    @configuration_provider(temp.name, must_exist=True)
    class TestClass(Configuration):
        x = Setting("x", 4, setting_type=int)

    with temp as fp:
        fp.write(yaml.dump({"x": "5"}))
        fp.flush()
        foo = TestClass.load(temp.name)
        assert foo.x == 5

    with pytest.raises(ValueError) as err:
        TestClass.load()

    assert "could not find configuration file at " + temp.name in str(err)


def test_environment_provider():
    @configuration_provider("$_dc_test")
    @configuration_provider({"x": "bar"})
    class TestClass(Configuration):
        x = Setting("x", "foo")

    # Fallback to default if no environment variable present
    assert TestClass.load().x == "bar"

    try:
        # Load from environment variable if present
        temp = tempfile.NamedTemporaryFile('w')
        os.environ["_dc_test"] = temp.name
        with temp as fp:
            fp.write(yaml.dump({"x": "5"}))
            fp.flush()
            foo = TestClass.load()
            assert foo.x == "5"

        # environment variable uses must_exist = true by default
        with pytest.raises(ValueError) as err:
            TestClass.load()
        assert "could not find configuration file at " + temp.name in str(err)
    finally:
        del os.environ["_dc_test"]


def test_nested_providers():
    @configuration_provider("$_dc_test")
    @configuration_provider({"x": "a"})
    class TestClass(Configuration):
        x = Setting("x", "foo")

    foo = TestClass.load()
    assert foo.x == "a"

    try:
        temp = tempfile.NamedTemporaryFile('w')
        os.environ["_dc_test"] = temp.name
        with temp as fp:
            fp.write(yaml.dump({"x": "5"}))
            fp.flush()
            foo = TestClass.load()
            assert foo.x == "5"
    finally:
        del os.environ["_dc_test"]
