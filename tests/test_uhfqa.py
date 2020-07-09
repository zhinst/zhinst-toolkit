import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import UHFQA, UHFQA_AWG, ReadoutChannel, DeviceTypes


def test_init_uhfqa():
    qa = UHFQA("name", "dev1234")
    assert qa.device_type == DeviceTypes.UHFQA
    assert qa._awg is not None
    assert len(qa.channels) == 10
    assert qa.integration_time is not None
    assert qa.result_source is not None
    with pytest.raises(Exception):
        qa._init_settings()


def test_init_uhfqa_awg():
    awg = UHFQA_AWG(UHFQA("name", "dev1234"), 0)
    assert awg.output1 is not None
    assert awg.output2 is not None
    assert awg.gain1 is not None
    assert awg.gain2 is not None
    assert awg.__repr__() != ""
    with pytest.raises(Exception):
        awg.outputs(["on", "on"])
    with pytest.raises(Exception):
        awg.outputs()
    with pytest.raises(Exception):
        awg.output1("on")
    with pytest.raises(Exception):
        awg.output1()
    with pytest.raises(Exception):
        awg.update_readout_params()
    with pytest.raises(Exception):
        awg.set_sequence_params(sequence_type="Readout")
        awg.update_readout_params()


@given(st.integers(12))
def test_init_readout_channel(i):
    if i not in range(10):
        with pytest.raises(ValueError):
            ch = ReadoutChannel(UHFQA("name", "dev1234"), i)
    else:
        ch = ReadoutChannel(UHFQA("name", "dev1234"), i)
        assert ch.index == i
        assert ch.rotation is not None
        assert ch.threshold is not None
        assert ch.result is not None
        assert not ch.enabled()
        assert ch.__repr__() != ""


def test_set_get_params_channel():
    ch = ReadoutChannel(UHFQA("name", "dev1234"), 0)
    assert ch.readout_frequency() == 100e6
    ch.readout_amplitude(0.5)
    assert ch.readout_amplitude() == 0.5
    ch.phase_shift(10)
    assert ch.phase_shift() == 10
    with pytest.raises(Exception):
        ch.enable()
    with pytest.raises(Exception):
        ch.disable()
    with pytest.raises(Exception):
        ch.readout_frequency(1)
