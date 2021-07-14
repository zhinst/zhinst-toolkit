# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, strategies as st
import numpy as np

from .context import (
    UHFQA,
    UHFQA_AWG,
    ReadoutChannel,
    DeviceTypes,
    SequenceType,
    TriggerMode,
    uhfqa_logger,
)

uhfqa_logger.disable_logging()


def test_init_uhfqa():
    qa = UHFQA("name", "dev2000")
    assert qa.device_type == DeviceTypes.UHFQA
    assert qa._awg is None
    assert qa.awg is None
    assert len(qa._channels) == 0
    assert len(qa.channels) == 0
    assert qa.integration_time is None
    assert qa.integration_length is None
    assert qa.result_source is None
    assert qa.averaging_mode is None
    assert qa.ref_clock is None
    assert qa._qa_delay_user == 0
    assert qa.allowed_sequences == [
        SequenceType.NONE,
        SequenceType.SIMPLE,
        SequenceType.READOUT,
        SequenceType.CW_SPEC,
        SequenceType.PULSED_SPEC,
        SequenceType.CUSTOM,
    ]
    assert qa.allowed_trigger_modes == [
        TriggerMode.NONE,
        TriggerMode.EXTERNAL_TRIGGER,
        TriggerMode.RECEIVE_TRIGGER,
        TriggerMode.ZSYNC_TRIGGER,
    ]
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_awg_cores()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_readout_channels()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_params()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_settings()


def test_methods_uhfqa():
    qa = UHFQA("name", "dev2000")
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.connect_device()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.factory_reset()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.arm()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.arm(length=1024)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.arm(averages=10)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.enable_qccs_mode()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.enable_manual_mode()


@given(delay_adj=st.integers(-300, 1300))
def test_qa_delay(delay_adj):
    qa = UHFQA("name", "dev2000")
    assert qa.qa_delay() == 0
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.qa_delay(delay_adj)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._qa_delay_default()


@given(rows=st.integers(1, 20), cols=st.integers(1, 20))
def test_crosstalk_matrix(rows, cols):
    qa = UHFQA("name", "dev2000")
    matrix = np.random.rand(rows, cols)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.crosstalk_matrix()
    if rows > 10 or cols > 10:
        with pytest.raises(ValueError):
            qa.crosstalk_matrix(matrix)
    else:
        with pytest.raises(uhfqa_logger.ToolkitConnectionError):
            qa.crosstalk_matrix(matrix)


@given(
    channels=st.lists(elements=st.integers(1, 9), min_size=1, max_size=10, unique=True)
)
def test_enable_readout_channels_correct_range(channels):
    qa = UHFQA("name", "dev2000")
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_readout_channels()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.enable_readout_channels(channels)


@given(
    channels=st.lists(
        elements=st.integers(10, 20), min_size=1, max_size=10, unique=True
    )
)
def test_enable_readout_channels_wrong_range(channels):
    qa = UHFQA("name", "dev2000")
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_readout_channels()
    with pytest.raises(ValueError):
        qa.enable_readout_channels(channels)


@given(
    channels=st.lists(elements=st.integers(1, 9), min_size=1, max_size=10, unique=True)
)
def test_disable_readout_channels_correct_range(channels):
    qa = UHFQA("name", "dev2000")
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_readout_channels()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa.disable_readout_channels(channels)


@given(
    channels=st.lists(
        elements=st.integers(10, 20), min_size=1, max_size=10, unique=True
    )
)
def test_disable_readout_channels_wrong_range(channels):
    qa = UHFQA("name", "dev2000")
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        qa._init_readout_channels()
    with pytest.raises(ValueError):
        qa.disable_readout_channels(channels)


def test_init_uhfqa_awg():
    awg = UHFQA_AWG(UHFQA("name", "dev2000"), 0)
    assert awg.output1 is None
    assert awg.output2 is None
    assert awg.gain1 is None
    assert awg.gain2 is None
    assert awg.single is None
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        awg._init_awg_params()


def test_repr_str_uhfqa_awg():
    awg = UHFQA_AWG(UHFQA("name", "dev2000"), 0)
    assert awg.__repr__() != ""


@given(
    sequence_type=st.sampled_from(SequenceType),
    trigger_mode=st.sampled_from(TriggerMode),
)
def test_uhfqa_awg_set_get(sequence_type, trigger_mode):
    awg = UHFQA_AWG(UHFQA("name", "dev2000"), 0)
    with pytest.raises(TypeError):
        awg.outputs(["on", "on"])
    with pytest.raises(ValueError):
        awg.outputs(["on"])
    with pytest.raises(ValueError):
        awg.outputs("on")
    with pytest.raises(TypeError):
        awg.outputs()
    with pytest.raises(ValueError):
        awg.set_sequence_params(sequence_type="text")
    if sequence_type in awg._parent.allowed_sequences:
        with pytest.raises(uhfqa_logger.ToolkitConnectionError):
            awg.set_sequence_params(sequence_type=sequence_type)
    else:
        with pytest.raises(uhfqa_logger.ToolkitError):
            awg.set_sequence_params(sequence_type=sequence_type)
    with pytest.raises(ValueError):
        awg.set_sequence_params(trigger_mode="text")
    if trigger_mode in awg._parent.allowed_trigger_modes:
        if trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
            TriggerMode.ZSYNC_TRIGGER,
        ]:
            with pytest.raises(uhfqa_logger.ToolkitConnectionError):
                awg.set_sequence_params(trigger_mode=trigger_mode)
        else:
            awg.set_sequence_params(trigger_mode=trigger_mode)
    else:
        with pytest.raises(uhfqa_logger.ToolkitError):
            awg.set_sequence_params(trigger_mode=trigger_mode)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        awg.compile()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        awg._apply_receive_trigger_settings()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        awg._apply_zsync_trigger_settings()


@given(sequence_type=st.sampled_from(SequenceType))
def test_update_readout_params(sequence_type):
    uhf = UHFQA("name", "dev2000")
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        uhf._init_awg_cores()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        uhf._init_readout_channels()
    if sequence_type in uhf.allowed_sequences:
        with pytest.raises(uhfqa_logger.ToolkitConnectionError):
            uhf.awg.set_sequence_params(sequence_type=sequence_type)
        if sequence_type == SequenceType.READOUT:
            with pytest.raises(uhfqa_logger.ToolkitConnectionError):
                uhf.channels[0].enable()
            uhf.awg.update_readout_params()
        else:
            with pytest.raises(uhfqa_logger.ToolkitError):
                uhf.awg.update_readout_params()


@given(i=st.integers(1, 20))
def test_init_readout_channel(i):
    if i not in range(10):
        with pytest.raises(ValueError):
            ReadoutChannel(UHFQA("name", "dev2000"), i)
    else:
        with pytest.raises(uhfqa_logger.ToolkitConnectionError):
            uhf = UHFQA("name", "dev2000")
            uhf._init_readout_channels()
        ch = uhf.channels[i]
        assert ch.index == i
        assert ch._parent == uhf
        assert not ch._enabled
        assert not ch.enabled()
        assert ch._readout_frequency == 100e6
        assert ch._readout_amplitude == 1
        assert ch._int_weights_envelope == 1.0
        assert ch._phase_shift == 0
        assert ch.rotation is None
        assert ch.threshold is None
        assert ch.result is None
        with pytest.raises(TypeError):
            ch.__repr__()
        with pytest.raises(uhfqa_logger.ToolkitConnectionError):
            ch._init_channel_params()


def test_set_get_params_channel():
    ch = ReadoutChannel(UHFQA("name", "dev2000"), 0)
    assert ch.readout_frequency() == 100e6
    ch.readout_amplitude(0.5)
    assert ch.readout_amplitude() == 0.5
    ch.phase_shift(10)
    assert ch.phase_shift() == 10
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch.enable()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch.disable()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch.readout_frequency(1)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch._set_int_weights()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch._reset_int_weights()
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch._average_result(1000)


@given(single_value=st.floats(-2, 2),)
def test_int_weights_envelope_single_value(single_value):
    ch = ReadoutChannel(UHFQA("name", "dev2000"), 0)
    with pytest.raises(uhfqa_logger.ToolkitConnectionError):
        ch.int_weights_envelope(single_value)
    if single_value < 0:
        assert ch.int_weights_envelope() == 0
    elif single_value > 1:
        assert ch.int_weights_envelope() == 1
    else:
        assert ch.int_weights_envelope() == single_value


@given(value_list=st.lists(st.floats(0, 1), min_size=1, max_size=4096),)
def test_int_weights_envelope_value_list(value_list):
    ch = ReadoutChannel(UHFQA("name", "dev2000"), 0)
    with pytest.raises(TypeError):
        ch.int_weights_envelope(value_list)


@given(length=st.integers(1, 5000), freq=st.floats(-1e9, 2e9), phase=st.integers(0, 90))
def test_demod_weights(length, freq, phase):
    ch = ReadoutChannel(UHFQA("name", "dev2000"), 0)
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
