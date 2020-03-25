# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
import json

from .context import InstrumentConfiguration, DeviceTypes


def test_init():
    config = InstrumentConfiguration()
    assert hasattr(config, "api_config")
    assert hasattr(config, "instrument")


def test_set_api_config():
    config = InstrumentConfiguration()
    api = config.api_config
    assert api.host == "localhost"
    assert api.port == 8004
    assert api.api == 6
    api.host = "10.42.12312"
    api.port = 8001
    api.api = 1
    assert api.host == "10.42.12312"
    assert api.port == 8001
    assert api.api == 1


def test_set_instr_config():
    config = InstrumentConfiguration()
    dev = config.instrument
    assert dev.name == "device0"
    conf = dev.config
    assert conf.serial == "dev#####"
    assert conf.device_type == DeviceTypes.HDAWG
    assert conf.interface == "1GbE"
    conf.serial = "dev1111"
    conf.device_type = DeviceTypes.UHFQA
    conf.interface = "usb"
    assert conf.serial == "dev1111"
    assert conf.device_type == DeviceTypes.UHFQA
    assert conf.interface == "usb"
