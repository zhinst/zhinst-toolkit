import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine

from helpers import Compiler
import numpy as np


class Device:
    def __init__(self, n, i):
        self.name = "hdawg0"
        self.connectivity = Connectivity(n)
        self.config = Config(i)


class Connectivity:
    def __init__(self, n):
        self.awgs = list()
        for i in range(n):
            self.awgs.append(AWG(i))


class AWG:
    def __init__(self, i):
        self.awg = i


class Config:
    def __init__(self, i):
        self.device_type = "uhfqa" if i else "hdawg"


@given(n=st.integers(1, 4), i=st.integers(0, 1))
def test_init(n, i):
    dev = Device(n, i)
    compiler = Compiler()
    compiler.add_device(dev)


class CompilerHDAWGMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.compiler = Compiler()
        self.compiler.add_device(Device(4, 1))

    @rule(type=st.integers(0, 3), awg=st.integers(0, 3))
    def change_type(self, type, awg):
        if type == 0:
            t = None
        elif type == 1:
            t = "Simple"
        elif type == 2:
            t = "T1"
        elif type == 3:
            t = "T2*"
        self.compiler.set_parameter("hdawg0", awg, sequence_type=t)
        assert self.compiler.sequence_type("hdawg0", awg) == t

    @rule(l=st.integers(1, 1000), amp=st.floats(0, 1.0), awg=st.integers(0, 3))
    def change_amps(self, l, amp, awg):
        test_array = np.random.uniform(0, amp, l)
        self.compiler.set_parameter("hdawg0", awg, pulse_amplitudes=test_array)
        params = self.compiler.list_params("hdawg0", awg)
        type = self.compiler.sequence_type("hdawg0", awg)
        params = params["sequence_parameters"]
        if type == "Rabi":
            assert np.array_equal(params["pulse_amplitudes"], test_array)
        else:
            assert "pulse_amplitudes" not in params.keys()

    @rule(l=st.integers(1, 1000), t=st.floats(100e-9, 10e-6), awg=st.integers(0, 3))
    def change_delays(self, l, t, awg):
        test_array = np.random.uniform(0, t, l)
        self.compiler.set_parameter("hdawg0", awg, delay_times=test_array)
        params = self.compiler.list_params("hdawg0", awg)
        type = self.compiler.sequence_type("hdawg0", awg)
        params = params["sequence_parameters"]
        if type in ["T1", "T2*"]:
            assert np.array_equal(params["delay_times"], test_array)
        else:
            assert "delay_times" not in params.keys()

    @rule(awg=st.integers(0, 3))
    def get_sequence(self, awg):
        sequence = self.compiler.get_program("hdawg0", awg)
        type = self.compiler.sequence_type("hdawg0", awg)
        if type is None:
            assert sequence is None
        else:
            assert type in sequence


class CompilerUHFQAMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.compiler = Compiler()
        self.compiler.add_device(Device(4, 0))

    @rule(type=st.integers(0, 3), awg=st.integers(0, 3))
    def change_type(self, type, awg):
        if type == 0:
            t = None
        elif type == 1:
            t = "Simple"
        elif type == 2:
            t = "T1"
        elif type == 3:
            t = "T2*"
        self.compiler.set_parameter("hdawg0", awg, sequence_type=t)
        assert self.compiler.sequence_type("hdawg0", awg) == t

    @rule(l=st.integers(1, 1000), amp=st.floats(0, 1.0), awg=st.integers(0, 3))
    def change_amps(self, l, amp, awg):
        test_array = np.random.uniform(0, amp, l)
        self.compiler.set_parameter("hdawg0", awg, pulse_amplitudes=test_array)
        params = self.compiler.list_params("hdawg0", awg)
        type = self.compiler.sequence_type("hdawg0", awg)
        params = params["sequence_parameters"]
        if type == "Rabi":
            assert np.array_equal(params["pulse_amplitudes"], test_array)
        else:
            assert "pulse_amplitudes" not in params.keys()

    @rule(l=st.integers(1, 1000), t=st.floats(100e-9, 10e-6), awg=st.integers(0, 3))
    def change_delays(self, l, t, awg):
        test_array = np.random.uniform(0, t, l)
        self.compiler.set_parameter("hdawg0", awg, delay_times=test_array)
        params = self.compiler.list_params("hdawg0", awg)
        type = self.compiler.sequence_type("hdawg0", awg)
        params = params["sequence_parameters"]
        if type in ["T1", "T2*"]:
            assert np.array_equal(params["delay_times"], test_array)
        else:
            assert "delay_times" not in params.keys()

    @rule(awg=st.integers(0, 3))
    def get_sequence(self, awg):
        sequence = self.compiler.get_program("hdawg0", awg)
        type = self.compiler.sequence_type("hdawg0", awg)
        if type is None:
            assert sequence is None
        else:
            assert type in sequence


TestPrograms1 = CompilerHDAWGMachine.TestCase
TestPrograms2 = CompilerUHFQAMachine.TestCase

