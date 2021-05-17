import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import PQSC, DeviceTypes


def test_init_pqsc():
    pqsc = PQSC("name", "dev1234")
    assert pqsc.device_type == DeviceTypes.PQSC
    assert pqsc.ref_clock is None
    assert pqsc.ref_clock_actual is None
    assert pqsc.ref_clock_status is None
    assert pqsc.progress is None
    with pytest.raises(Exception):
        pqsc._init_params()


def test_methods_pqsc():
    pqsc = PQSC("name", "dev1234")
    with pytest.raises(Exception):
        pqsc.connect_device()
    with pytest.raises(Exception):
        pqsc.factory_reset()
    with pytest.raises(Exception):
        pqsc.arm()
    with pytest.raises(Exception):
        pqsc.run()
    with pytest.raises(Exception):
        pqsc.stop()
    with pytest.raises(Exception):
        pqsc.check_ref_clock()
