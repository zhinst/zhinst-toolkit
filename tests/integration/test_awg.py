import pytest
from hypothesis import given, assume, settings, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine

from helpers import AWG
from helpers.awg import NotConnectedError, CompilationFailedError
import zhinst.utils
import numpy as np


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
    assert not awg.in_use
    awg.setup(daq, dev)
    assert awg.awg_module_executed
    assert awg.in_use
    assert awg.index == 0
    del daq
    del awg


def test_sequence_upload_fail(awg):
    program = "this = should fail"
    with pytest.raises(Exception):
        awg._upload_program(program)


@given(t=st.integers(1, 3))
@settings(deadline=1000)
def test_sequence_upload(awg, t):
    if t == 1:
        type = "Rabi"
        awg.set(sequence_type=type)
        awg.set(pulse_amplitudes=np.linspace(0, 1.0, 20))
    elif t == 2:
        type = "T1"
        awg.set(sequence_type=type)
        awg.set(delay_times=np.linspace(0, 5e-6, 20))
    elif t == 3:
        type = "T2*"
        awg.set(sequence_type=type)
        awg.set(delay_times=np.linspace(0, 5e-6, 20))
    awg.update()


def test_sequence_upload_Simple_before_addWaveform(awg):
    awg.set(sequence_type="Simple")
    awg.set(buffer_lengths=[800] * 24)
    with pytest.raises(Exception):
        awg.update()

@given(n=st.integers(1, 10))
@settings(deadline=10000, max_examples=100)
def test_simple_sequence_upload_n_waveforms(awg, n):
    awg.set(sequence_type="Simple")
    for i in range(n):
        awg.add_waveform(np.ones(80), np.ones(80))
    awg.upload_waveforms()

# @given(lenghts=st.lists(st.integers(100, 200), min_size=1, max_size=10))
# @settings(deadline=1000, max_examples=10)
# def test_simple_sequence_upload_different_waveforms(awg, lenghts):
#     awg.set(sequence_type="Simple")
#     for l in lenghts:        
#         awg.add_waveform(np.ones(l), np.ones(l))
#     awg.upload_waveforms()



