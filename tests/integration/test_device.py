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
    daq = dev._Device__daq
    settings = daq.listNodesJSON("*", settingsonly=True)
    node_dict = json.loads(settings)
    node_list = []
    for key, value in node_dict.items():
        if "Integer" in value["Type"] and "Write" in value["Properties"]:
            node_list.append(key)
    yield node_list
    del daq


@pytest.fixture(scope="session")
def nodes_double(dev):
    daq = dev._Device__daq
    settings = daq.listNodesJSON("*", settingsonly=True)
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


@given(i=st.integers(0, 475))
@settings(deadline=500, max_examples=50)
def test_get_set_integer(dev, i, nodes_int):
    node = nodes_int[i] 
    temp = dev.get(node)
    dev.set(node, temp)
    assert dev.get(node) == temp


@given(i=st.integers(0, 284))
@settings(deadline=500, max_examples=50)
def test_get_set_double(dev, i, nodes_double):
    node = nodes_double[i] 
    temp = dev.get(node)
    dev.set(node, temp)
    assert round(dev.get(node), 5) == round(temp, 5)


@pytest.mark.skip
def test_get_set_vector(dev):
    pass


def test_set_command_list_def(dev):
    dev.set([])
    dev.set("sigouts/0/on", 1)
    dev.set("sigouts/0/on", 0)
    dev.set([("sigouts/0/on", 1), ("sigouts/0/on", 0)])
    with pytest.raises(Exception):
        dev.set([("blub")])
        dev.set(["asdfasd"])
        dev.set([0])


def test_command_defs(dev):
    command = "sigouts/0/on"
    dev.set(command, 0)
    assert dev.get(command) == 0
    command = "/sigouts/0/on"
    dev.set(command, 0)
    assert dev.get(command) == 0
    command = "dev8030/sigouts/0/on"
    dev.set(command, 0)
    assert dev.get(command) == 0
    command = "/dev8030/sigouts/0/on"
    dev.set(command, 0)
    assert dev.get(command) == 0
    command = "sigouts/0/xyz"
    with pytest.raises(RuntimeError):
        dev.set(command, 0)
    







