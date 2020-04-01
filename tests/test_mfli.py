import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import MFLI, DeviceTypes


def test_init_uhfqa():
    mf = MFLI("name", "dev1234")
    assert mf.device_type == DeviceTypes.MFLI
