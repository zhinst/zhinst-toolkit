import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import Parameter, ToolkitNodeTreeError


DUMMY_PARAMETER = {
    "Node": "test/bla/blub",
}


class Device:
    def __init__(self):
        self.serial = ""
        self._value = None

    def _get(self, path):
        return self._value

    def _set(self, path, v):
        self._value = v
        return self._value


class Parent:
    def __init__(self, dev):
        self._device = dev


def test_parameter_init():
    dev = Device()
    parent = Parent(dev)
    p = Parameter(parent, DUMMY_PARAMETER)
    assert p._parent == parent
    assert p._device == dev


def test_parameter_details():
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Description"] = "TEST"
    params["Type"] = "TEST"
    params["Properties"] = "Read, Write"
    params["Options"] = "TEST"
    params["Unit"] = "TEST"
    p = Parameter(parent, DUMMY_PARAMETER)
    assert p.__repr__() != ""


@given(st.integers())
def test_set_get(v):
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Properties"] = "Read, Write"
    p = Parameter(parent, DUMMY_PARAMETER)
    p(v)
    assert p() == v


def test_set_get_readonly():
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Properties"] = "Read"
    p = Parameter(parent, DUMMY_PARAMETER)
    p()
    with pytest.raises(ToolkitNodeTreeError):
        p(0)


@given(st.integers())
def test_set_get_writeonly(v):
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Properties"] = "Write"
    p = Parameter(parent, DUMMY_PARAMETER)
    p(v)
    with pytest.raises(ToolkitNodeTreeError):
        p()
