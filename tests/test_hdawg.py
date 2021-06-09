import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import HDAWG, HDAWG_AWG, DeviceTypes, SequenceType, TriggerMode


def test_init_hdawg():
    hd = HDAWG("name", "dev1234")
    assert len(hd._awgs) == 0
    assert len(hd.awgs) == 0
    assert hd.device_type == DeviceTypes.HDAWG
    assert hd.ref_clock is None
    assert hd.ref_clock_status is None
    with pytest.raises(Exception):
        hd._init_awg_cores()
    with pytest.raises(Exception):
        hd._init_params()
    hd._init_settings()


def test_methods_hdawg():
    hd = HDAWG("name", "dev1234")
    with pytest.raises(Exception):
        hd.connect_device()
    with pytest.raises(Exception):
        hd.factory_reset()
    with pytest.raises(Exception):
        hd.enable_qccs_mode()
    with pytest.raises(Exception):
        hd.enable_manual_mode()


def test_init_hdawg_awg():
    awg = HDAWG_AWG(HDAWG("name", "dev1234"), 0)
    assert awg._iq_modulation is False
    assert awg.output1 is None
    assert awg.output2 is None
    assert awg.gain1 is None
    assert awg.gain2 is None
    assert awg.modulation_freq is None
    assert awg.modulation_phase_shift is None
    with pytest.raises(Exception):
        awg._init_awg_params()


@given(i=st.booleans())
def test_repr_str_hdawg_awg(i):
    awg = HDAWG_AWG(HDAWG("name", "dev1234"), 0)
    awg._iq_modulation = i
    if i:
        with pytest.raises(Exception):
            awg.__repr__()
    else:
        assert "IQ Modulation DISABLED" in awg.__repr__()


@given(
    sequence_type=st.sampled_from(
        [SequenceType.READOUT, SequenceType.PULSED_SPEC, SequenceType.CW_SPEC]
    ),
    trigger_mode=st.sampled_from(
        [TriggerMode.ZSYNC_TRIGGER, TriggerMode.RECEIVE_TRIGGER]
    ),
)
def test_hdawg_awg_set_get(sequence_type, trigger_mode):
    awg = HDAWG_AWG(HDAWG("name", "dev1234"), 0)
    with pytest.raises(Exception):
        awg.outputs(["on", "on"])
    with pytest.raises(Exception):
        awg.outputs(["on"])
    with pytest.raises(Exception):
        awg.outputs("on")
    with pytest.raises(Exception):
        awg.outputs()
    with pytest.raises(Exception):
        awg.output1("on")
    with pytest.raises(Exception):
        awg.output1()
    with pytest.raises(Exception):
        awg.enable_iq_modulation()
    with pytest.raises(Exception):
        awg.disable_iq_modulation()
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
