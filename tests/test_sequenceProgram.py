# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import SequenceProgram


class SequenceProgramMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.sequenceProgram = SequenceProgram()

    @rule(type=st.integers(0, 7))
    def change_type(self, type):
        if type == 0:
            t = None
        elif type == 1:
            t = "Simple"
        elif type == 2:
            t = "T1"
        elif type == 3:
            t = "T2*"
        elif type == 4:
            t = "Readout"
        elif type == 5:
            t = "Custom"
        elif type == 6:
            t = "CW Spectroscopy"
        elif type == 7:
            t = "Pulsed Spectroscopy"
        self.sequenceProgram.set_params(sequence_type=t)
        assert self.sequenceProgram.sequence_type == t

    @rule(l=st.integers(1, 1000), amp=st.floats(0, 1.0))
    def change_amps(self, l, amp):
        test_array = np.random.uniform(0, amp, l)
        self.sequenceProgram.set_params(pulse_amplitudes=test_array)
        params = self.sequenceProgram.list_params()
        if self.sequenceProgram.sequence_type == "Rabi":
            assert np.array_equal(
                params["sequence_parameters"]["pulse_amplitudes"], test_array
            )
        else:
            assert "pulse_amplitudes" not in params["sequence_parameters"].keys()

    # @rule(l=st.integers(1, 1000), t=st.floats(100e-9, 10e-6))
    # def change_delays(self, l, t):
    #     test_array = np.linspace(0, t, l)
    #     self.sequenceProgram.set_params(delay_times=test_array)
    #     params = self.sequenceProgram.list_params()
    #     if self.sequenceProgram.sequence_type in ["T1", "T2*"]:
    #         assert np.array_equal(
    #             params["sequence_parameters"]["delay_times"], test_array
    #         )
    #     else:
    #         assert "delay_times" not in params["sequence_parameters"].keys()

    @rule()
    def get_sequence(self):
        sequence = self.sequenceProgram.get_seqc()
        if self.sequenceProgram.sequence_type is None:
            assert sequence is None
        else:
            assert self.sequenceProgram.sequence_type in sequence


TestPrograms = SequenceProgramMachine.TestCase

