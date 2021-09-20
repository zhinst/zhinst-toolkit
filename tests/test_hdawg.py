import pytest
from hypothesis import given, strategies as st

from .context import (
    HDAWG,
    HDAWG_AWG,
    DeviceTypes,
    SequenceType,
    TriggerMode,
    hdawg_logger,
)

hdawg_logger.disable_logging()


def test_init_hdawg():
    hd = HDAWG("name", "dev8000")
    assert len(hd._awgs) == 0
    assert len(hd.awgs) == 0
    assert hd.device_type == DeviceTypes.HDAWG
    assert hd.ref_clock is None
    assert hd.ref_clock_status is None
    assert hd.allowed_sequences == [
        SequenceType.NONE,
        SequenceType.SIMPLE,
        SequenceType.TRIGGER,
        SequenceType.RABI,
        SequenceType.T1,
        SequenceType.T2,
        SequenceType.CUSTOM,
    ]
    assert hd.allowed_trigger_modes == [
        TriggerMode.NONE,
        TriggerMode.SEND_TRIGGER,
        TriggerMode.EXTERNAL_TRIGGER,
        TriggerMode.RECEIVE_TRIGGER,
        TriggerMode.SEND_AND_RECEIVE_TRIGGER,
        TriggerMode.ZSYNC_TRIGGER,
    ]
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        hd._init_awg_cores()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        hd._init_params()
    hd._init_settings()


def test_methods_hdawg():
    hd = HDAWG("name", "dev8000")
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        hd.connect_device()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        hd.factory_reset()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        hd.enable_qccs_mode()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        hd.enable_manual_mode()


def test_init_hdawg_awg():
    awg = HDAWG_AWG(HDAWG("name", "dev8000"), 0)
    assert awg.ct is None
    assert awg._iq_modulation is False
    assert awg.output1 is None
    assert awg.output2 is None
    assert awg.gain1 is None
    assert awg.gain2 is None
    assert awg.modulation_freq is None
    assert awg.modulation_phase_shift is None
    assert awg.single is None
    assert awg.zsync_register_mask is None
    assert awg.zsync_register_shift is None
    assert awg.zsync_register_offset is None
    assert awg.zsync_decoder_mask is None
    assert awg.zsync_decoder_shift is None
    assert awg.zsync_decoder_offset is None
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        awg._init_awg_params()


@given(i=st.booleans())
def test_repr_str_hdawg_awg(i):
    awg = HDAWG_AWG(HDAWG("name", "dev8000"), 0)
    awg._iq_modulation = i
    if i:
        with pytest.raises(TypeError):
            awg.__repr__()
    else:
        assert "IQ Modulation DISABLED" in awg.__repr__()


@given(
    sequence_type=st.sampled_from(SequenceType),
    trigger_mode=st.sampled_from(TriggerMode),
)
def test_hdawg_awg_set_get(sequence_type, trigger_mode):
    awg = HDAWG_AWG(HDAWG("name", "dev8000"), 0)
    with pytest.raises(TypeError):
        awg.outputs(["on", "on"])
    with pytest.raises(ValueError):
        awg.outputs(["on"])
    with pytest.raises(ValueError):
        awg.outputs("on")
    with pytest.raises(TypeError):
        awg.outputs()
    with pytest.raises(TypeError):
        awg.output1("on")
    with pytest.raises(TypeError):
        awg.output1()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        awg.enable_iq_modulation()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        awg.disable_iq_modulation()
    with pytest.raises(ValueError):
        awg.set_sequence_params(sequence_type="text")
    if sequence_type in awg._parent.allowed_sequences:
        awg.set_sequence_params(sequence_type=sequence_type)
    else:
        with pytest.raises(hdawg_logger.ToolkitError):
            awg.set_sequence_params(sequence_type=sequence_type)
    with pytest.raises(ValueError):
        awg.set_sequence_params(trigger_mode="text")
    if trigger_mode in awg._parent.allowed_trigger_modes:
        if trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
            TriggerMode.ZSYNC_TRIGGER,
        ]:
            with pytest.raises(hdawg_logger.ToolkitConnectionError):
                awg.set_sequence_params(trigger_mode=trigger_mode)
        else:
            awg.set_sequence_params(trigger_mode=trigger_mode)
    else:
        with pytest.raises(hdawg_logger.ToolkitError):
            awg.set_sequence_params(trigger_mode=trigger_mode)
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        awg._apply_receive_trigger_settings()
    with pytest.raises(hdawg_logger.ToolkitConnectionError):
        awg._apply_zsync_trigger_settings()
