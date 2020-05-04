import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import DAQModule, ToolkitError


class Parent:
    def _get_streamingnodes(self):
        return "streamingnodes"


def test_daq_init():
    p = Parent()
    daq = DAQModule(p)
    assert daq._parent == p
    assert daq._module is None
    assert not daq.signals
    assert not daq.results
    assert daq._signal_sources == "streamingnodes"
    assert daq._signal_types


def test_no_connection():
    p = Parent()
    daq = DAQModule(p)
    with pytest.raises(ToolkitError):
        daq._init_settings()
    with pytest.raises(ToolkitError):
        daq._set("endless", 0)
    with pytest.raises(ToolkitError):
        daq._get("endless")
