import pytest
from hypothesis import given, assume, settings, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine

from drivers.device import Device, DeviceTypeError
import zhinst.utils
import numpy as np
import time
import json


@pytest.fixture(scope="session")
def dev():
    dev = Device()
    dev.connect("dev8030", "HDAWG")
    yield dev
    del dev


@pytest.fixture(scope="session")
def nodes_int(dev):
    daq = dev._daq
    settings = daq.listNodesJSON("*", settingsonly=True)
    #json_string = settings.replace("\/", "/")
    node_dict = json.loads(settings)
    node_list = []
    for key, value in node_dict.items():
        if "Integer" in value["Type"] and "Write" in value["Properties"]:
            node_list.append(key)
    yield node_list
    del daq


@pytest.fixture(scope="session")
def nodes_double(dev):
    daq = dev._daq
    settings = daq.listNodesJSON("*", settingsonly=True)
    #json_string = settings.replace("\/", "/")
    node_dict = json.loads(settings)
    node_list = []
    for key, value in node_dict.items():
        if "Double" in value["Type"] and "Write" in value["Properties"]:
            node_list.append(key)
    yield node_list
    del daq


def test_device_connect():
    address = "dev8030"
    dev = Device()
    dev.connect("")
    with pytest.raises(DeviceTypeError):
        dev.connect(address)
    with pytest.raises(Exception):
        dev.connect(address, "UHFQA")
    dev.connect(address, "HDAWG")


@given(lst=st.lists(st.integers(0, 491), 20, 20, unique=True))
@settings(deadline=5000, max_examples=5)
def test_get_set_integer(dev, lst, nodes_int):
    for l in lst:
        node = nodes_int[l] 
        temp = dev.get_node_value(node)
        comp = dev.set_node_value(node, temp)
        assert comp == temp


@given(lst=st.lists(st.integers(0, 284), 20, 20, unique=True))
@settings(deadline=5000, max_examples=5)
def test_get_set_double(dev, lst, nodes_double):
    for l in lst:
        node = nodes_double[l] 
        temp = dev.get_node_value(node)
        comp = dev.set_node_value(node, temp)
        assert comp == temp


@pytest.mark.skip
def test_get_set_vector(dev):
    pass


@pytest.mark.skip
def test_get_set_complex(dev, nodes_complex):
    pass


def test_command_defs(dev):
    command = "sigouts/0/on"
    dev.set_node_value(command, 0)
    assert dev.get_node_value(command) == 0
    command = "/sigouts/0/on"
    dev.set_node_value(command, 0)
    assert dev.get_node_value(command) == 0
    command = "dev8030/sigouts/0/on"
    dev.set_node_value(command, 0)
    assert dev.get_node_value(command) == 0
    command = "/dev8030/sigouts/0/on"
    dev.set_node_value(command, 0)
    assert dev.get_node_value(command) == 0
    command = "sigouts/0/xyz"
    with pytest.raises(TypeError):
        dev.set_node_value(command, 0)
    







