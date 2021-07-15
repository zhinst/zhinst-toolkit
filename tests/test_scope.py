# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, strategies as st

from .context import (
    Scope,
    scope_logger,
    parser_logger,
    connection_logger,
    DeviceTypes,
    UHFQA,
    UHFLI,
    MFLI,
)

scope_logger.disable_logging()
parser_logger.disable_logging()
connection_logger.disable_logging()


@given(device_type=st.sampled_from(DeviceTypes),)
def test_init_scope(device_type):
    allowed_device_types = {
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
        DeviceTypes.MFLI: MFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        scope = Scope(instr)
        assert scope._parent == instr
        assert scope._module is None


@given(device_type=st.sampled_from(DeviceTypes))
def test_scope_connection(device_type):
    allowed_device_types = {
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
        DeviceTypes.MFLI: MFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        scope = Scope(instr)
        with pytest.raises(scope_logger.ToolkitConnectionError):
            scope._setup()
        with pytest.raises(scope_logger.ToolkitConnectionError):
            scope._init_scope_settings()
        scope._init_scope_params()


@given(device_type=st.sampled_from(DeviceTypes))
def test_scope_methods(device_type):
    allowed_device_types = {
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
        DeviceTypes.MFLI: MFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        scope = Scope(instr)
        with pytest.raises(scope_logger.ToolkitConnectionError):
            scope.arm()
        with pytest.raises(AttributeError):
            scope.run()
        with pytest.raises(scope_logger.ToolkitConnectionError):
            scope.arm_and_run()
        with pytest.raises(AttributeError):
            scope.stop()
        with pytest.raises(AttributeError):
            scope.wait_done()
        with pytest.raises(AttributeError):
            scope.read()
        with pytest.raises(AttributeError):
            scope.is_running


@given(device_type=st.sampled_from(DeviceTypes))
def test_scope_set_get(device_type):
    allowed_device_types = {
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
        DeviceTypes.MFLI: MFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        scope = Scope(instr)
        with pytest.raises(AttributeError):
            scope.channels()
        with pytest.raises(AttributeError):
            scope.channels(["on", "on"])
        with pytest.raises(ValueError):
            scope.channels(["off", "off"])
        with pytest.raises(ValueError):
            scope.channels(["on"])
        with pytest.raises(ValueError):
            scope.channels("on")
        with pytest.raises(AttributeError):
            scope.mode()
        with pytest.raises(AttributeError):
            scope.mode("time")
        with pytest.raises(AttributeError):
            scope.num_records()
        with pytest.raises(AttributeError):
            scope.num_records(5)
        with pytest.raises(AttributeError):
            scope.averager_weight()
        with pytest.raises(AttributeError):
            scope.averager_weight(10)
