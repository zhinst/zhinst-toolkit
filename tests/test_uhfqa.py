import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import (
    UHFQA,
    UHFQA_AWG,
    ReadoutChannel,
    DeviceTypes,
    SequenceType,
    TriggerMode,
)


def test_init_uhfqa():
    qa = UHFQA("name", "dev1234")
    assert qa.device_type == DeviceTypes.UHFQA
    assert qa._awg is None
    assert qa.awg is None
    assert len(qa._channels) == 0
    assert len(qa.channels) == 0
    assert qa.integration_time is None
    assert qa.result_source is None
    with pytest.raises(Exception):
        qa._init_awg_cores()
    with pytest.raises(Exception):
        qa._init_readout_channels()
    with pytest.raises(Exception):
        qa._init_params()
    with pytest.raises(Exception):
        qa._init_settings()


def test_methods_uhfqa():
    qa = UHFQA("name", "dev1234")
    with pytest.raises(Exception):
        qa.connect_device()
    with pytest.raises(Exception):
        qa.factory_reset()
    with pytest.raises(Exception):
        qa.arm()
    with pytest.raises(Exception):
        qa.arm(length=1024)
    with pytest.raises(Exception):
        qa.arm(averages=10)
    with pytest.raises(Exception):
        qa.enable_qccs_mode()
    with pytest.raises(Exception):
        qa.enable_manual_mode()


@given(delay_adj=st.integers(-300, 1300))
def test_qa_delay(delay_adj):
    qa = UHFQA("name", "dev1234")
    assert 0 == qa.qa_delay()
    with pytest.raises(Exception):
        qa.qa_delay(delay_adj)


@given(rows=st.integers(1, 20), cols=st.integers(1, 20))
def test_crosstalk_matrix(rows, cols):
    qa = UHFQA("name", "dev1234")
    matrix = np.random.rand(rows, cols)
    with pytest.raises(Exception):
        qa.crosstalk_matrix()
    with pytest.raises(Exception):
        qa.crosstalk_matrix(matrix)


@given(channels=st.lists(elements=st.integers(1, 20), min_size=1, max_size=10))
def test_enable_readout_channels(channels):
    qa = UHFQA("name", "dev1234")
    with pytest.raises(Exception):
        qa.enable_readout_channels(channels)


@given(channels=st.lists(elements=st.integers(1, 20), min_size=1, max_size=10))
def test_disable_readout_channels(channels):
    qa = UHFQA("name", "dev1234")
    with pytest.raises(Exception):
        qa.disable_readout_channels(channels)


@given(
    sequence_type=st.sampled_from(SequenceType),
    trigger_mode=st.sampled_from(
        [TriggerMode.ZSYNC_TRIGGER, TriggerMode.RECEIVE_TRIGGER]
    ),
)
def test_init_uhfqa_awg(sequence_type, trigger_mode):
    awg = UHFQA_AWG(UHFQA("name", "dev1234"), 0)
    assert awg.output1 is None
    assert awg.output2 is None
    assert awg.gain1 is None
    assert awg.gain2 is None
    assert awg.__repr__() != ""
    with pytest.raises(Exception):
        awg.outputs(["on", "on"])
    with pytest.raises(Exception):
        awg.outputs(["on"])
    with pytest.raises(Exception):
        awg.outputs("on")
    with pytest.raises(Exception):
        awg.outputs()
    with pytest.raises(Exception):
        awg.update_readout_params()
    with pytest.raises(Exception):
        awg.compile()
    with pytest.raises(Exception):
        awg.set_sequence_params(sequence_type="text")
    with pytest.raises(Exception):
        awg.set_sequence_params(sequence_type=sequence_type)
    with pytest.raises(Exception):
        awg.set_sequence_params(trigger_mode="text")
    with pytest.raises(Exception):
        awg.set_sequence_params(trigger_mode=trigger_mode)
    with pytest.raises(Exception):
        awg._apply_receive_trigger_settings()
    with pytest.raises(Exception):
        awg._apply_zsync_trigger_settings()
    with pytest.raises(Exception):
        awg._init_awg_params()


@given(i=st.integers(1, 20))
def test_init_readout_channel(i):
    if i not in range(10):
        with pytest.raises(ValueError):
            ch = ReadoutChannel(UHFQA("name", "dev1234"), i)
    else:
        ch = ReadoutChannel(UHFQA("name", "dev1234"), i)
        assert ch.index == i
        assert ch.rotation is None
        assert ch.threshold is None
        assert ch.result is None
        assert not ch.enabled()
        with pytest.raises(Exception):
            ch.__repr__()
    with pytest.raises(Exception):
        ch._init_channel_params()


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
    with pytest.raises(Exception):
        ch._set_int_weights()
    with pytest.raises(Exception):
        ch._reset_int_weights()
    with pytest.raises(Exception):
        ch._average_result(1000)


@given(length=st.integers(1, 5000), freq=st.floats(-1e9, 2e9), phase=st.integers(0, 90))
def test_demod_weights(length, freq, phase):
    ch = ReadoutChannel(UHFQA("name", "dev1234"), 0)
    if length > 4096:
        with pytest.raises(ValueError):
            ch._demod_weights(length, 1.0, freq, phase)
    elif freq <= 0:
        with pytest.raises(ValueError):
            ch._demod_weights(length, 1.0, freq, phase)
    else:
        clk_rate = 1.8e9
        x = np.arange(0, length)
        y = np.sin(2 * np.pi * freq * x / clk_rate + np.deg2rad(phase))
        assert max(abs(y - ch._demod_weights(length, 1.0, freq, phase))) < 1e-3
