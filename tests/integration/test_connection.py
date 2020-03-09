# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
from pytest import fixture
import json
import time

from .context import ziDrivers


SERIAL = "dev8030"
SERIAL_QA = "dev2266"
INTERFACE = "1gbe"


@fixture()
def connection_hdawg():
    instrument_config = "ziDrivers/resources/connection-hdawg.json"
    with open(instrument_config) as file:
        data = json.load(file)
        schema = ziDrivers.interface.InstrumentConfiguration()
        config = schema.load(data)
        con = ziDrivers.connection.ZIDeviceConnection(config.api_configs[0].details)
        yield con
        del con


@fixture()
def connection_uhfqa():
    instrument_config = "ziDrivers/resources/connection-uhfqa.json"
    with open(instrument_config) as file:
        data = json.load(file)
        schema = ziDrivers.interface.InstrumentConfiguration()
        config = schema.load(data)
        con = ziDrivers.connection.ZIDeviceConnection(config.api_configs[0].details)
        yield con
        del con


def test_connect_hdawg(connection_hdawg):
    connection_hdawg.connect()


def test_connect_uhfqa(connection_uhfqa):
    connection_uhfqa.connect()


def test_connect_device_hdawg(connection_hdawg):
    connection_hdawg.connect()
    with pytest.raises(Exception):
        connection_hdawg.connect_device()
        connection_hdawg.connect_device(serial=SERIAL)
    with pytest.raises(RuntimeError):
        connection_hdawg.connect_device(serial="ajdf", interface=INTERFACE)
        connection_hdawg.connect_device(serial=SERIAL, interface="asdhf")
    connection_hdawg.connect_device(serial=SERIAL, interface=INTERFACE)


def test_connect_device_uhfqa(connection_uhfqa):
    connection_uhfqa.connect()
    with pytest.raises(Exception):
        connection_uhfqa.connect_device()
        connection_uhfqa.connect_device(serial=SERIAL_QA)
    with pytest.raises(RuntimeError):
        connection_uhfqa.connect_device(serial="ajdf", interface=INTERFACE)
        connection_uhfqa.connect_device(serial=SERIAL_QA, interface="asdhf")
    connection_uhfqa.connect_device(serial=SERIAL_QA, interface=INTERFACE)


def test_get_set(connection_hdawg):
    connection_hdawg.connect()
    connection_hdawg.connect_device(serial=SERIAL, interface=INTERFACE)
    time.sleep(1)
    data = connection_hdawg.get("/" + SERIAL + "/sigouts/*/on", flat=True)
    for d in data.values():
        assert d["value"][0] == 0
    connection_hdawg.set([("/" + SERIAL + "/sigouts/*/on", 1)])
    data = connection_hdawg.get("/" + SERIAL + "/sigouts/*/on", flat=True)
    for d in data.values():
        assert d["value"][0] == 1
    time.sleep(1)
    connection_hdawg.set([("/" + SERIAL + "/sigouts/*/on", 0)])
    data = connection_hdawg.get("/" + SERIAL + "/sigouts/*/on", flat=True)
    for d in data.values():
        assert d["value"][0] == 0


def test_awg_module_init(connection_hdawg):
    assert connection_hdawg.awg_module is None
    connection_hdawg.connect()
    time.sleep(1)
    assert connection_hdawg.awg_module is not None
    assert connection_hdawg.awg_module.device == ""
    assert connection_hdawg.awg_module.index == 0


def test_awg_module_device_update(connection_hdawg):
    connection_hdawg.connect()
    connection_hdawg.connect_device(serial=SERIAL, interface=INTERFACE)
    time.sleep(1)
    assert connection_hdawg.awg_module.device == SERIAL
    assert connection_hdawg.awg_module.index == 0
    connection_hdawg.awg_module.update(index=1, device="test")
    assert connection_hdawg.awg_module.index == 1
    assert connection_hdawg.awg_module.device == "test"


def test_awg_module_set_get_int(connection_hdawg):
    connection_hdawg.connect()
    connection_hdawg.connect_device(serial=SERIAL, interface=INTERFACE)
    time.sleep(1)
    connection_hdawg.awg_module.set("/index", 2)
    assert connection_hdawg.awg_module.get_int("/index") == 2
    connection_hdawg.awg_module.set("/index", 0)
    assert connection_hdawg.awg_module.get_int("/index") == 0


def test_awg_module_set_get_string(connection_hdawg):
    connection_hdawg.connect()
    connection_hdawg.connect_device(serial=SERIAL, interface=INTERFACE)
    time.sleep(1)
    connection_hdawg.awg_module.set("/device", "test")
    with pytest.raises(RuntimeError):
        connection_hdawg.awg_module.get_string("/device")
    connection_hdawg.awg_module.set("/device", SERIAL)
    assert connection_hdawg.awg_module.get_string("/device") == SERIAL
    connection_hdawg.awg_module.get_string("/directory")


def test_awg_module_get_double(connection_hdawg):
    connection_hdawg.connect()
    connection_hdawg.connect_device(serial=SERIAL, interface=INTERFACE)
    time.sleep(1)
    connection_hdawg.awg_module.get_double("/progress")

