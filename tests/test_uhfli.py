# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, strategies as st

from .context import (
    UHFLI,
    UHFQA_AWG,
    DeviceTypes,
    SequenceType,
    TriggerMode,
    uhfli_logger,
    uhfqa_logger,
    awg_logger,
    baseinstrument_logger,
    connection_logger,
    parser_logger,
)

uhfli_logger.disable_logging()
uhfqa_logger.disable_logging()
baseinstrument_logger.disable_logging()
connection_logger.disable_logging()
parser_logger.disable_logging()
awg_logger.disable_logging()


def test_init_uhfqa():
    li = UHFLI("name", "dev2000")
    assert li.device_type == DeviceTypes.UHFLI
    assert li._awg is None
    li._options = []
    with pytest.raises(uhfli_logger.ToolkitError):
        li.awg
    li._options = ["AWG"]
    assert li.awg is None
    assert li._daq is None
    assert li.daq is None
    assert li._sweeper is None
    assert li.sweeper is None
    assert li.allowed_sequences == [
        SequenceType.NONE,
        SequenceType.SIMPLE,
        SequenceType.CW_SPEC,
        SequenceType.PULSED_SPEC,
        SequenceType.CUSTOM,
    ]
    assert li.allowed_trigger_modes == [
        TriggerMode.NONE,
        TriggerMode.EXTERNAL_TRIGGER,
        TriggerMode.RECEIVE_TRIGGER,
        TriggerMode.ZSYNC_TRIGGER,
    ]
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li._init_awg_cores()
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li._init_daq()
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li._init_sweeper()
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li._init_params()
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li._init_settings()


def test_methods_uhfli():
    li = UHFLI("name", "dev2000")
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li.connect_device()
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        li.factory_reset()


def test_init_uhfli_awg():
    li = UHFLI("name", "dev2000")
    li._options = ["AWG"]
    awg = UHFQA_AWG(li, 0)
    assert awg.output1 is None
    assert awg.output2 is None
    assert awg.gain1 is None
    assert awg.gain2 is None
    assert awg.single is None
    with pytest.raises(uhfli_logger.ToolkitConnectionError):
        awg._init_awg_params()


def test_repr_str_uhfli_awg():
    li = UHFLI("name", "dev2000")
    li._options = ["AWG"]
    awg = UHFQA_AWG(li, 0)
    assert awg.__repr__() != ""


@given(
    sequence_type=st.sampled_from(SequenceType),
    trigger_mode=st.sampled_from(TriggerMode),
)
def test_uhfqa_awg_set_get(sequence_type, trigger_mode):
    li = UHFLI("name", "dev2000")
    li._options = ["AWG"]
    awg = UHFQA_AWG(li, 0)
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
        with pytest.raises(uhfli_logger.ToolkitConnectionError):
            awg.set_sequence_params(sequence_type=sequence_type)
    else:
        with pytest.raises(uhfli_logger.ToolkitError):
            awg.set_sequence_params(sequence_type=sequence_type)
    with pytest.raises(ValueError):
        awg.set_sequence_params(trigger_mode="text")
    if trigger_mode in awg._parent.allowed_trigger_modes:
        if trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
            TriggerMode.ZSYNC_TRIGGER,
        ]:
            with pytest.raises(uhfli_logger.ToolkitConnectionError):
                awg.set_sequence_params(trigger_mode=trigger_mode)
        else:
            awg.set_sequence_params(trigger_mode=trigger_mode)
    else:
        with pytest.raises(uhfli_logger.ToolkitError):
            awg.set_sequence_params(trigger_mode=trigger_mode)
    if (
        sequence_type in awg._parent.allowed_sequences
        and trigger_mode in awg._parent.allowed_trigger_modes
    ):
        with pytest.raises(uhfli_logger.ToolkitConnectionError):
            awg.compile()
        with pytest.raises(uhfli_logger.ToolkitConnectionError):
            awg._apply_receive_trigger_settings()
        with pytest.raises(uhfli_logger.ToolkitConnectionError):
            awg._apply_zsync_trigger_settings()
