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
)

awg_logger.disable_logging()


@given(st.integers(0, 3), st.integers(0, 2))
def test_init_awg(i, j):
    device_types = {
        0: HDAWG,
        1: UHFQA,
        2: UHFLI,
    }
    device = device_types[j]
    instr = device("name", "dev1234")
    awg = AWGCore(instr, i)
    assert awg._parent == instr
    assert awg._index == i
    assert awg.waveforms == []
    assert awg.name == f"name-awg-{i}"
    assert awg._program is not None
    params = awg.sequence_params["sequence_parameters"]
    if j == 0:
        assert params["target"] == DeviceTypes.HDAWG
    elif j == 1:
        assert params["target"] == DeviceTypes.UHFQA
    elif j == 2:
        assert params["target"] == DeviceTypes.UHFLI
    strings = ["parent", "index", "sequence", "type"]
    assert any(s in awg.__repr__() for s in strings)


@given(st.integers(0, 3))
def test_awg_connection(i):
    instr = HDAWG("name", "dev1234")
    awg = AWGCore(instr, i)
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.is_running
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.run()
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.stop()
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.wait_done()
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.compile()
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.upload_waveforms()
    with pytest.raises(awg_logger.ToolkitConnectionError):
        awg.compile_and_upload_waveforms()


@given(sequence_type=st.sampled_from(SequenceType),)
def test_awg_waveform(sequence_type):
    instr = HDAWG("name", "dev1234")
    awg = AWGCore(instr, 0)
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
