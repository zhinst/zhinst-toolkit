import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import HDAWG, HDAWG_AWG, DeviceTypes, SequenceType


def test_init_hdawg():
    hd = HDAWG("name", "dev1234")
    assert len(hd._awgs) == 4
    assert hd.device_type == DeviceTypes.HDAWG
    with pytest.raises(Exception):
        hd._init_settings()


def test_init_hdawg_awg():
    awg = HDAWG_AWG(HDAWG("name", "dev1234"), 0)
    assert awg.output1 is not None
    assert awg.output2 is not None
    assert awg.gain1 is not None
    assert awg.gain2 is not None
    assert awg.modulation_freq is not None
    assert awg.modulation_phase_shift is not None
    assert awg.__repr__() != ""


def test_hdawg_awg_set_get():
    awg = HDAWG_AWG(HDAWG("name", "dev1234"), 0)
    with pytest.raises(Exception):
        awg.outputs(["on", "on"])
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
        awg._apply_sequence_settings(sequence_type="1234")
    with pytest.raises(Exception):
        awg._apply_sequence_settings(sequence_type=SequenceType.READOUT)
    with pytest.raises(Exception):
        awg._apply_trigger_settings()
