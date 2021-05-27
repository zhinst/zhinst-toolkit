import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import UHFLI, UHFLI_AWG, DeviceTypes


def test_init_uhfqa():
    li = UHFLI("name", "dev1234")
    assert li.device_type == DeviceTypes.UHFLI
    assert li._awg is not None
    with pytest.raises(Exception):
        li._init_settings()


def test_init_uhfqa_awg():
    awg = UHFLI_AWG(UHFLI("name", "dev1234"), 0)
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
        awg.set_sequence_params(sequence_type="Pulse Train")
