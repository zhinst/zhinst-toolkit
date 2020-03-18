import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import DAQModule, ZHTKException


def test_init_daq():
    daq = DAQModule("parent")
    assert daq._parent == "parent"
    assert daq._module is None


def test_no_connection():
    daq = DAQModule("parent")
    with pytest.raises(ZHTKException):
        daq._get("device")
    with pytest.raises(ZHTKException):
        daq._set("device", "dev1234")

