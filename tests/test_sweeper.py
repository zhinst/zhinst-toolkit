import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import SweeperModule, ToolkitError


class Parent:
    def _get_streamingnodes(self):
        return "streamingnodes"


def test_sweeper_init():
    p = Parent()
    s = SweeperModule(p)
    assert s._parent == p
    assert s._module is None
    assert not s.signals
    assert not s.results
    assert s._signal_sources == "streamingnodes"
    assert not s._sweep_params


def test_no_connection():
    p = Parent()
    s = SweeperModule(p)
    with pytest.raises(ToolkitError):
        s._init_settings()
    with pytest.raises(ToolkitError):
        s._set("endless", 0)
    with pytest.raises(ToolkitError):
        s._get("endless")
