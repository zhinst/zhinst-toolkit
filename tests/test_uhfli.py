import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import UHFLI, DeviceTypes


def test_init_uhfqa():
    li = UHFLI("name", "dev1234")
    assert li.device_type == DeviceTypes.UHFLI
