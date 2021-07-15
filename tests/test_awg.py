# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, strategies as st

from .context import (
    AWGCore,
    HDAWG,
    UHFQA,
    UHFLI,
    DeviceTypes,
    SequenceType,
    awg_logger,
    parser_logger,
    connection_logger,
    baseinstrument_logger,
)

awg_logger.disable_logging()
parser_logger.disable_logging()
connection_logger.disable_logging()
baseinstrument_logger.disable_logging()


@given(device_type=st.sampled_from(DeviceTypes), index=st.integers(0, 3))
def test_init_awg(device_type, index):
    allowed_device_types = {
        DeviceTypes.HDAWG: HDAWG,
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        instr._options = ["AWG"]
        awg = AWGCore(instr, index)
        assert awg._parent == instr
        assert awg._index == index
        assert awg._module is None
        assert awg._waveforms == []
        assert awg._program is not None
        assert awg.index == index
        assert awg.name == f"name-awg-{index}"
        assert awg.waveforms == []
        params = awg.sequence_params["sequence_parameters"]
        assert params["target"] == device_type
        strings = ["parent", "index", "sequence", "type"]
        assert any(s in awg.__repr__() for s in strings)


@given(device_type=st.sampled_from(DeviceTypes), index=st.integers(0, 3))
def test_awg_connection(device_type, index):
    allowed_device_types = {
        DeviceTypes.HDAWG: HDAWG,
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        instr._options = ["AWG"]
        awg = AWGCore(instr, index)
        with pytest.raises(awg_logger.ToolkitConnectionError):
            awg._setup()
        awg._init_awg_params()


@given(device_type=st.sampled_from(DeviceTypes), index=st.integers(0, 3))
def test_awg_methods(device_type, index):
    allowed_device_types = {
        DeviceTypes.HDAWG: HDAWG,
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        instr._options = ["AWG"]
        awg = AWGCore(instr, index)
        with pytest.raises(AttributeError):
            awg.run()
        with pytest.raises(AttributeError):
            awg.stop()
        with pytest.raises(AttributeError):
            awg.wait_done()
        with pytest.raises(awg_logger.ToolkitConnectionError):
            awg.compile()
        with pytest.raises(awg_logger.ToolkitConnectionError):
            awg.upload_waveforms()
        with pytest.raises(awg_logger.ToolkitConnectionError):
            awg.compile_and_upload_waveforms()
        with pytest.raises(AttributeError):
            awg.is_running


@given(device_type=st.sampled_from(DeviceTypes), index=st.integers(0, 3))
def test_awg_set_get(device_type, index):
    allowed_device_types = {
        DeviceTypes.HDAWG: HDAWG,
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        instr._options = ["AWG"]
        awg = AWGCore(instr, index)
        with pytest.raises(AttributeError):
            awg.outputs()
        with pytest.raises(AttributeError):
            awg.outputs(["on", "on"])
        with pytest.raises(ValueError):
            awg.outputs(["on"])
        with pytest.raises(ValueError):
            awg.outputs("on")


@given(
    device_type=st.sampled_from(DeviceTypes),
    sequence_type=st.sampled_from(SequenceType),
    index=st.integers(0, 3),
)
def test_awg_waveform(device_type, sequence_type, index):
    allowed_device_types = {
        DeviceTypes.HDAWG: HDAWG,
        DeviceTypes.UHFQA: UHFQA,
        DeviceTypes.UHFLI: UHFLI,
    }
    if device_type in allowed_device_types.keys():
        device = allowed_device_types[device_type]
        instr = device("name", "dev1234")
        instr._options = ["AWG"]
        awg = AWGCore(instr, index)
        if sequence_type in instr.allowed_sequences:
            awg.set_sequence_params(sequence_type=sequence_type)
            if sequence_type in [SequenceType.SIMPLE, SequenceType.CUSTOM]:
                awg.queue_waveform([], [])
                assert len(awg.waveforms) == 1
                awg.reset_queue()
                assert awg.waveforms == []
                for i in range(10):
                    awg.queue_waveform([], [])
                assert len(awg.waveforms) == 10
                awg.queue_waveform([-1] * 80, [-1] * 80)
                awg.replace_waveform([1] * 80, [1] * 80, i=10)
                wave = awg.waveforms[10].data
                assert any(w == (2 ** (15) - 1) for w in wave)
            else:
                with pytest.raises(awg_logger.ToolkitError):
                    awg.queue_waveform([], [])
                assert awg.waveforms == []
