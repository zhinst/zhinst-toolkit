import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import (
    ZIConnection,
    DeviceConnection,
    ToolkitConnectionError,
    DeviceTypes,
)


class Details:
    host = "something"
    port = 1234
    api = 5


class Config:
    _api_config = Details()


class Device:
    _config = Config()
    serial = "dev###"
    interface = "usb"
    device_type = DeviceTypes.HDAWG

class DiscoveryMock:
    def find(self, serial):
        return serial.upper()
    
    def get(self, serial):
        assert(serial == serial.upper())
        return { "deviceid": serial }

def test_init_zi_connection():
    c = ZIConnection(Details())
    assert not c.established
    assert c._daq is None
    assert c._awg is None


def test_check_connection():
    c = ZIConnection(Details())
    with pytest.raises(ToolkitConnectionError):
        c.connect_device()
    with pytest.raises(ToolkitConnectionError):
        c.get("tests/test")
    with pytest.raises(ToolkitConnectionError):
        c.get_sample("tests/test")
    with pytest.raises(ToolkitConnectionError):
        c.set("tests/test", 1)
    with pytest.raises(ToolkitConnectionError):
        c.connect()


def test_init_device_connection():
    dev = Device()
    c = DeviceConnection(dev, DiscoveryMock())
    assert c._connection == None
    assert c._device == dev


def test_device_connection_connect():
    c = DeviceConnection(Device(), DiscoveryMock())
    with pytest.raises(ToolkitConnectionError):
        c.setup()
    with pytest.raises(ToolkitConnectionError):
        c.setup(connection=ZIConnection(Details()))
    with pytest.raises(ToolkitConnectionError):
        c.connect_device()
    with pytest.raises(ToolkitConnectionError):
        c.get("tests/test")
    with pytest.raises(ToolkitConnectionError):
        c.set("tests/test", 1)
    with pytest.raises(ToolkitConnectionError):
        c.get_nodetree("*")

def test_device_normalized_serial():
    c = DeviceConnection(Device(), DiscoveryMock())
    assert c.normalized_serial is None