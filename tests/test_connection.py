import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import (
    ZIConnection,
    DeviceConnection,
    ZHTKConnectionException,
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


def test_init_zi_connection():
    c = ZIConnection(Details())
    assert not c.established
    assert c._daq is None
    assert c._awg is None


def test_check_connection():
    c = ZIConnection(Details())
    with pytest.raises(ZHTKConnectionException):
        c.connect_device()
    with pytest.raises(ZHTKConnectionException):
        c.get("tests/test")
    with pytest.raises(ZHTKConnectionException):
        c.get_sample("tests/test")
    with pytest.raises(ZHTKConnectionException):
        c.set("tests/test", 1)
    with pytest.raises(ZHTKConnectionException):
        c.connect()


def test_init_device_connection():
    dev = Device()
    c = DeviceConnection(dev)
    assert c._connection == None
    assert c._device == dev


def test_device_connection_connect():
    c = DeviceConnection(Device())
    with pytest.raises(ZHTKConnectionException):
        c.setup()
    with pytest.raises(ZHTKConnectionException):
        c.setup(connection=ZIConnection(Details()))
    with pytest.raises(ZHTKConnectionException):
        c.connect_device()
    with pytest.raises(ZHTKConnectionException):
        c.get("tests/test")
    with pytest.raises(ZHTKConnectionException):
        c.set("tests/test", 1)
    with pytest.raises(ZHTKConnectionException):
        c.get_nodetree("*")
