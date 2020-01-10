import pytest
from hypothesis import given, assume, settings, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine

from drivers.awg import AWG
from drivers.awg import NotConnectedError, CompilationFailedError
from helpers import SequenceProgram
import zhinst.utils
import numpy as np
import time


@pytest.fixture(scope="session")
def connection():
    daq = zhinst.utils.autoConnect(default_port=8004, api_level=6)
    dev = zhinst.utils.autoDetect(daq)
    yield (daq, dev)
    del daq


@pytest.fixture(scope="session")
def awg():
    daq = zhinst.utils.autoConnect(default_port=8004, api_level=6)
    dev = zhinst.utils.autoDetect(daq)
    awg = AWG()
    awg.setup(daq, dev)
    yield awg
    del daq
    del awg


def test_setup_awg(connection):
    awg = AWG()
    daq, dev = connection
    assert not awg.awg_module_executed
    awg.setup(daq, dev)
    assert awg.awg_module_executed
    assert awg.index == 0
    del daq
    del awg


def test_sequence_upload_fail(awg):
    program = "this = should fail"
    with pytest.raises(Exception):
        awg.upload_program(program)


@given(t=st.integers(1, 3))
@settings(deadline=1000)
def test_sequence_upload(awg, t):
    s = SequenceProgram()
    if t == 1:
        type = "Rabi"
        s.set(sequence_type=type)
        s.set(pulse_amplitudes=np.linspace(0, 1.0, 20))
    elif t == 2:
        type = "T1"
        s.set(sequence_type=type)
        s.set(delay_times=np.linspace(0, 5e-6, 20))
    elif t == 3:
        type = "T2*"
        s.set(sequence_type=type)
        s.set(delay_times=np.linspace(0, 5e-6, 20))
    program = s.get()
    awg.upload_program(program)


@given(n=st.integers(1, 3))
@settings(deadline=10000, max_examples=5)
def test_simple_sequence_run_stop(awg, n):
    s = SequenceProgram()
    s.set(sequence_type="Rabi", pulse_amplitudes=np.linspace(-1, 1, 100), period=1)
    awg.upload_program(s.get())
    for _ in range(n):
        awg.run()
        time.sleep(0.5)
        assert awg.is_running
        awg.stop()
        assert not awg.is_running
        time.sleep(0.5)


# @given(length=st.integers(1, 100))
# @settings(deadline=10000, max_examples=10)
# def test_simple_sequence_uploaded_waveform_matches(connection, length):
#     daq, dev = connection
#     awg = AWG()
#     awg.setup(daq, dev)
#     awg.set(sequence_type="Simple")
#     wave1 = np.ones(length)
#     wave2 = np.ones(length)
#     awg.add_waveform(wave1, wave2)
#     awg.upload_waveforms()
#     node = "/{}/awgs/0/waveform/waves/0".format(dev)
#     d = daq.get(node, flat=True, settingsonly=False)
#     vec = d[node][0]["vector"]
#     vec1 = vec[::2]
#     vec2 = vec[1::2]
#     vec1 = vec1[: len(wave1)]
#     vec2 = vec2[: len(wave2)]
#     wave1 = (wave1 * (2 ** 15 - 1)).astype("uint16")
#     wave2 = (wave2 * (2 ** 15 - 1)).astype("uint16")
#     assert np.array_equal(wave1, vec1)
#     assert np.array_equal(wave2, vec2)


# @given(lenghts=st.lists(st.integers(100, 200), min_size=1, max_size=10))
# @settings(deadline=1000, max_examples=10)
# def test_simple_sequence_upload_different_waveforms(awg, lenghts):
#     awg.set(sequence_type="Simple")
#     for l in lenghts:
#         awg.add_waveform(np.ones(l), np.ones(l))
#     awg.upload_waveforms()

