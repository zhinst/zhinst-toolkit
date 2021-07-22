# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, strategies as st

from .context import Parse, Parameter, nodetree_logger, parser_logger

nodetree_logger.disable_logging()
parser_logger.disable_logging()


DUMMY_PARAMETER = {
    "Node": "test/bla/blub",
}

DUMMY_OPTIONS = {
    "1": '"result_of_integration": Complex-valued integration results of the Weighted '
    "Integration in Qubit Readout mode.",
    "3": '"result_of_discrimination": The results after state discrimination.',
}

DUMMY_OPTIONS2 = {
    "0": '"chan0trigin0", "channel0_trigger_input0": Channel 1, Trigger Input A.',
    "1024": '"swtrig0", "software_trigger0": Software Trigger 0.',
}

DUMMY_SET_PARSER = [
    lambda v: Parse.greater_equal(v, 4),
    lambda v: Parse.multiple_of(v, 4, "down"),
]


class Device:
    def __init__(self):
        self.serial = ""
        self._value = None

    def _get(self, path):
        return self._value

    def _set(self, path, v, sync):
        self._value = v
        return self._value

    def _assert_node_value(self, path, v, blocking, timeout, sleep_time):
        print(v, self._get(path))
        if v == self._get(path):
            return True
        else:
            return False


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
    params["Options"] = DUMMY_OPTIONS
    params["Unit"] = "TEST"
    p = Parameter(parent, DUMMY_PARAMETER)
    assert p.__repr__() != ""
    p = Parameter(parent, DUMMY_PARAMETER, auto_mapping=True)
    assert p._map == {1: "result_of_integration", 3: "result_of_discrimination"}
    assert p._display_mapping is False
    params["Options"] = DUMMY_OPTIONS2
    p = Parameter(parent, DUMMY_PARAMETER, auto_mapping=True)
    assert p._map == {
        0: ["chan0trigin0", "channel0_trigger_input0"],
        1024: ["swtrig0", "software_trigger0"],
    }
    assert p._display_mapping is False
    p = Parameter(parent, DUMMY_PARAMETER, mapping={0: "key"})
    assert p._map == {0: "key"}
    assert p._display_mapping is True
    params["Options"] = None
    with pytest.raises(nodetree_logger.ToolkitNodeTreeError):
        Parameter(parent, DUMMY_PARAMETER, auto_mapping=True)


@given(st.integers())
def test_set_get(v):
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Properties"] = "Read, Write"
    p = Parameter(parent, DUMMY_PARAMETER)
    p(v)
    assert p() == v
    assert p.assert_value(v) is True
    p = Parameter(parent, DUMMY_PARAMETER, set_parser=DUMMY_SET_PARSER)
    p(5)
    assert p() == 4
    assert p.assert_value(4) is True
    p = Parameter(parent, DUMMY_PARAMETER, mapping={0: "key"})
    p("key")
    assert p() == "key"
    assert p.assert_value("key") is True
    p(0)
    assert p() == "key"
    assert p.assert_value("key") is True
    with pytest.raises(ValueError):
        p(1)
    with pytest.raises(ValueError):
        p("key2")
    params["Options"] = DUMMY_OPTIONS
    p = Parameter(parent, DUMMY_PARAMETER, auto_mapping=True)
    p(1)
    assert p() == "result_of_integration"
    assert p.assert_value("result_of_integration") is True
    with pytest.raises(ValueError):
        p(2)
    params["Options"] = DUMMY_OPTIONS2
    p = Parameter(parent, DUMMY_PARAMETER, auto_mapping=True)
    p(0)
    assert p() == "chan0trigin0"
    assert p.assert_value("chan0trigin0") is True
    with pytest.raises(ValueError):
        p(1)



def test_set_get_readonly():
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Properties"] = "Read"
    p = Parameter(parent, DUMMY_PARAMETER)
    p()
    with pytest.raises(nodetree_logger.ToolkitNodeTreeError):
        p(0)


@given(st.integers())
def test_set_get_writeonly(v):
    dev = Device()
    parent = Parent(dev)
    params = DUMMY_PARAMETER
    params["Properties"] = "Write"
    p = Parameter(parent, DUMMY_PARAMETER)
    p(v)
    with pytest.raises(nodetree_logger.ToolkitNodeTreeError):
        p()
