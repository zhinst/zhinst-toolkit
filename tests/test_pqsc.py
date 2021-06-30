# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st

from .context import PQSC, DeviceTypes, pqsc_logger

pqsc_logger.disable_logging()


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
    with pytest.raises(pqsc_logger.ToolkitConnectionError):
        pqsc._init_params()
    pqsc._init_settings()
    with pytest.raises(TypeError):
        pqsc.is_running


def test_methods_pqsc():
    pqsc = PQSC("name", "dev10000")
    with pytest.raises(pqsc_logger.ToolkitConnectionError):
        pqsc.connect_device()
    with pytest.raises(pqsc_logger.ToolkitConnectionError):
        pqsc.factory_reset()
    with pytest.raises(TypeError):
        pqsc.arm()
    with pytest.raises(TypeError):
        pqsc.arm(repetitions=100)
    with pytest.raises(TypeError):
        pqsc.arm(holdoff=2e-6)
    with pytest.raises(TypeError):
        pqsc.run()
    with pytest.raises(TypeError):
        pqsc.stop()
    with pytest.raises(TypeError):
        pqsc.wait_done()
    with pytest.raises(TypeError):
        pqsc.check_ref_clock()


@given(single_port=st.integers(0, 17),)
def test_check_zsync_connection_single_port(single_port):
    pqsc = PQSC("name", "dev10000")
    with pytest.raises(pqsc_logger.ToolkitConnectionError):
        pqsc.check_zsync_connection(ports=single_port)


@given(port_list=st.lists(st.integers(0, 17), min_size=1, max_size=18, unique=True),)
def test_check_zsync_connection_port_list(port_list):
    pqsc = PQSC("name", "dev10000")
    with pytest.raises(pqsc_logger.ToolkitConnectionError):
        pqsc.check_zsync_connection(ports=port_list)
