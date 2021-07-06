# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest

from .context import ZIConnection, DeviceConnection, DeviceTypes, connection_logger

connection_logger.disable_logging()


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
        assert serial == serial.upper()
        return {"deviceid": serial}


def test_init_zi_connection():
    c = ZIConnection(Details())
    assert not c.established
    assert c._daq is None
    assert c._awg_module is None
    assert c._daq_module is None
    assert c._sweeper_module is None
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.daq
    assert c.awg_module is None
    assert c.daq_module is None
    assert c.sweeper_module is None


def test_check_connection():
    c = ZIConnection(Details())
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.connect_device()
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.get("tests/test")
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.get_sample("tests/test")
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.set("tests/test", 1)
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.set_vector("tests/test", [1, 2, 3])
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.list_nodes()
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.connect()


def test_init_device_connection():
    dev = Device()
    discovery = DiscoveryMock()
    c = DeviceConnection(dev, discovery)
    assert c._connection is None
    assert c._device == dev
    assert c._normalized_serial is None
    assert c._discovery == discovery
    assert c._is_established is False
    assert c._is_connected is False
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.connection
    assert c.device == dev
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.normalized_serial
    assert c.discovery == discovery
    assert c.is_established is False
    assert c.is_connected is False


def test_device_connection_connect():
    c = DeviceConnection(Device(), DiscoveryMock())
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.setup()
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.setup(connection=ZIConnection(Details()))
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.connect_device()
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.get("tests/test")
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.set("tests/test", 1)
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.set_vector("tests/test", [1, 2, 3])
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.get_nodetree("*")


def test_device_normalized_serial():
    c = DeviceConnection(Device(), DiscoveryMock())
    with pytest.raises(connection_logger.ToolkitConnectionError):
        c.normalized_serial
