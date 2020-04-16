# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import SequenceProgram, SequenceType, TriggerMode, Alignment


class SequenceProgramMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.sequenceProgram = SequenceProgram()

    @rule(t=st.integers(0, 9))
    def change_sequence_by_enum(self, t):
        types = {
            0: SequenceType.NONE,
            1: SequenceType.SIMPLE,
            2: SequenceType.T1,
            3: SequenceType.T2,
            4: SequenceType.READOUT,
            5: SequenceType.CUSTOM,
            6: SequenceType.CW_SPEC,
            7: SequenceType.PULSED_SPEC,
            8: SequenceType.TRIGGER,
            9: SequenceType.RABI,
        }
        self.sequenceProgram.set_params(sequence_type=types[t])
        assert self.sequenceProgram.sequence_type == types[t]

    @rule(t=st.integers(-1, 9))
    def change_sequence_by_string(self, t):
        types = {
            -1: "None",
            0: None,
            1: "Simple",
            2: "T1",
            3: "T2*",
            4: "Readout",
            5: "Custom",
            6: "CW Spectroscopy",
            7: "Pulsed Spectroscopy",
            8: "Trigger",
            9: "Rabi",
        }
        self.sequenceProgram.set_params(sequence_type=types[t])
        if t == -1:
            assert self.sequenceProgram.sequence_type.value is None
        else:
            assert self.sequenceProgram.sequence_type.value == types[t]

    @rule(t=st.integers(0, 2))
    def change_trigger_by_enum(self, t):
        types = {
            0: TriggerMode.NONE,
            1: TriggerMode.SEND_TRIGGER,
            2: TriggerMode.EXTERNAL_TRIGGER,
        }
        self.sequenceProgram.set_params(trigger_mode=types[t])
        params = self.sequenceProgram.list_params()
        if params["sequence_type"] != SequenceType.TRIGGER:
            params = params["sequence_parameters"]
            assert params["trigger_mode"] == types[t]

    @rule(t=st.integers(-1, 2))
    def change_trigger_by_string(self, t):
        types = {
            -1: "None",
            0: None,
            1: "Send Trigger",
            2: "External Trigger",
        }
        self.sequenceProgram.set_params(trigger_mode=types[t])
        params = self.sequenceProgram.list_params()
        if params["sequence_type"] != SequenceType.TRIGGER:
            params = params["sequence_parameters"]
            if t == -1:
                assert params["trigger_mode"].value is None
            else:
                assert params["trigger_mode"].value == types[t]

    @rule(t=st.integers(0, 1))
    def change_alignment_by_enum(self, t):
        types = {
            0: Alignment.START_WITH_TRIGGER,
            1: Alignment.END_WITH_TRIGGER,
        }
        self.sequenceProgram.set_params(alignment=types[t])
        params = self.sequenceProgram.list_params()
        params = params["sequence_parameters"]
        assert params["alignment"] == types[t]

    @rule(t=st.integers(0, 1))
    def change_alignment_by_string(self, t):
        types = {
            0: "Start with Trigger",
            1: "End with Trigger",
        }
        self.sequenceProgram.set_params(alignment=types[t])
        params = self.sequenceProgram.list_params()
        params = params["sequence_parameters"]
        assert params["alignment"].value == types[t]

    @rule(l=st.integers(1, 1000), amp=st.floats(0, 1.0))
    def change_amps(self, l, amp):
        test_array = np.random.uniform(0, amp, l)
        self.sequenceProgram.set_params(pulse_amplitudes=test_array)
        params = self.sequenceProgram.list_params()
        if self.sequenceProgram.sequence_type == SequenceType.RABI:
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
        t = self.sequenceProgram.sequence_type.value
        if t is None:
            assert sequence is None
        else:
            assert t in sequence


TestPrograms = SequenceProgramMachine.TestCase
