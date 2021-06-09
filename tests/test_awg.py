import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import AWGCore, HDAWG, UHFQA, UHFLI, SequenceProgram, DeviceTypes


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
    with pytest.raises(Exception):
        awg.is_running
    with pytest.raises(Exception):
        awg.run()
    with pytest.raises(Exception):
        awg.stop()
    with pytest.raises(Exception):
        awg.wait_done()
    with pytest.raises(Exception):
        awg.compile()
    with pytest.raises(Exception):
        awg.upload_waveforms()
    with pytest.raises(Exception):
        awg.compile_and_upload_waveforms()


def test_awg_waveform():
    instr = HDAWG("name", "dev1234")
    awg = AWGCore(instr, 0)
    with pytest.raises(Exception):
        awg.queue_waveform([], [])
    assert awg.waveforms == []
    awg.set_sequence_params(sequence_type="Simple")
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
