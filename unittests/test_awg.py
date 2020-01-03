import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine

from helpers import AWG
from helpers.awg import NotConnectedError
import numpy as np


class TestAWG:
    def test_init_awg(self):
        awg = AWG()
        assert awg.waveforms == []
        assert awg.in_use == False
        assert "None" in awg.get_sequence()

    @given(st.floats(10e-6, 1), st.integers(1, 1000), st.integers(0, 3))
    def test_set_params(self, p, r, t):
        awg = AWG()
        awg.set(period=p)
        awg.set(repetitions=r)
        awg.set(n_HW_loop=100)

        if t == 0:
            type = "Simple"
            awg.set(sequence_type=type)
            awg.set(buffer_lengths=[800] * 24)
        elif t == 1:
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

        params = awg.sequence_params
        seq_params = params["sequence_parameters"]

        assert params["sequence_type"] == type
        assert seq_params["period"] == p
        assert seq_params["repetitions"] == r
        if t == 0:
            assert seq_params["n_HW_loop"] == len(seq_params["buffer_lengths"])
        if t == 1:
            assert seq_params["n_HW_loop"] == len(seq_params["pulse_amplitudes"])
        if t in [2, 3]:
            assert seq_params["n_HW_loop"] == len(seq_params["delay_times"])


class AWGMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.awg = AWG()

    @rule(type=st.integers(0, 3))
    def change_type(self, type):
        if type == 0:
            t = "Simple"
        elif type == 1:
            t = "Rabi"
        elif type == 2:
            t = "T1"
        elif type == 3:
            t = "T2*"
        self.awg.set(sequence_type=t)
        assert self.awg.sequence_params["sequence_type"] == t

    @rule()
    @precondition(lambda self: len(self.awg.waveforms) > 0)
    def update_awg(self):
        with pytest.raises(NotConnectedError):
            self.awg.update()
            if self.awg.sequence_params["sequence_type"] == "Simple":
                assert (
                    len(self.awg.waveforms)
                    == self.awg.sequence_params["sequence_parameters"]["n_HW_loop"]
                )
            if self.awg.sequence_params["sequence_type"] == "Rabi":
                assert (
                    len(self.awg.sequence_params["sequence_parameters"]["pulse_amplitudes"])
                    == self.awg.sequence_params["sequence_parameters"]["n_HW_loop"]
                )
            if self.awg.sequence_params["sequence_type"] in ["T1", "T2*"]:
                assert (
                    len(self.awg.sequence_params["sequence_parameters"]["delay_times"])
                    == self.awg.sequence_params["sequence_parameters"]["n_HW_loop"]
                )

    @rule(l=st.integers(0, 1000))
    def add_waveform(self, l):
        self.awg.add_waveform(np.ones(l), np.ones(l))

    @rule()
    @precondition(lambda self: len(self.awg.waveforms) > 0)
    def upload_waveforms(self):
        with pytest.raises(NotConnectedError):
            self.awg.upload_waveforms()
            assert self.awg.waveforms == []

    @rule()
    def get_sequence(self):
        s = self.awg.get_sequence()
        if self.awg.sequence_params["sequence_type"] is None:
            assert "None" in s
        else:
            assert self.awg.sequence_params["sequence_type"] in s

    @rule(test=st.integers())
    def overwrite_props(self, test):
        with pytest.raises(AttributeError):
            self.awg.waveforms = test
            self.awg.index = test
            self.awg.sequence_params = test

TestPrograms = AWGMachine.TestCase
