import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import PQSC, DeviceTypes


def test_init_pqsc():
    pqsc = PQSC("name", "dev10000")
    assert pqsc.device_type == DeviceTypes.PQSC
    assert pqsc.ref_clock is None
    assert pqsc.ref_clock_actual is None
    assert pqsc.ref_clock_status is None
    assert pqsc.progress is None
    assert pqsc._enable is None
    assert pqsc.repetitions is None
    assert pqsc.holdoff is None
    with pytest.raises(Exception):
        pqsc._init_params()
    pqsc._init_settings()
    with pytest.raises(Exception):
        pqsc.is_running


def test_methods_pqsc():
    pqsc = PQSC("name", "dev10000")
    with pytest.raises(Exception):
        pqsc.connect_device()
    with pytest.raises(Exception):
        pqsc.factory_reset()
    with pytest.raises(Exception):
        pqsc.arm()
    with pytest.raises(Exception):
        pqsc.arm(repetitions=100)
    with pytest.raises(Exception):
        pqsc.arm(holdoff=2e-6)
    with pytest.raises(Exception):
        pqsc.run()
    with pytest.raises(Exception):
        pqsc.stop()
    with pytest.raises(Exception):
        pqsc.wait_done()
    with pytest.raises(Exception):
        pqsc.check_ref_clock()


@given(
    single_port=st.integers(0, 17),
    port_list=st.lists(st.integers(0, 17), min_size=1, max_size=18, unique=True),
)
def test_check_zsync_connection(single_port, port_list):
    pqsc = PQSC("name", "dev10000")
    with pytest.raises(Exception):
        pqsc.check_zsync_connection(ports=single_port)
    with pytest.raises(Exception):
        pqsc.check_zsync_connection(ports=port_list)
