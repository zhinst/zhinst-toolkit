# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import SequenceProgram, SequenceType, TriggerMode, Alignment, DeviceTypes


class SequenceProgramMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.sequenceProgram = SequenceProgram()

    @rule(t=st.integers(1, 3))
    def change_device_type(self, t):
        types = {
            1: DeviceTypes.HDAWG,
            2: DeviceTypes.UHFQA,
            3: DeviceTypes.UHFLI,
        }
        self.sequenceProgram.set_params(target=types[t])
        params = self.sequenceProgram.list_params()
        target = params["sequence_parameters"]["target"]
        assert target == types[t]

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

    @rule(t=st.integers(0, 5))
    def change_trigger_by_enum(self, t):
        types = {
            0: TriggerMode.NONE,
            1: TriggerMode.SEND_TRIGGER,
            2: TriggerMode.EXTERNAL_TRIGGER,
            3: TriggerMode.RECEIVE_TRIGGER,
            4: TriggerMode.SEND_AND_RECEIVE_TRIGGER,
            5: TriggerMode.ZSYNC_TRIGGER,
        }
        self.sequenceProgram.set_params(trigger_mode=types[t])
        params = self.sequenceProgram.list_params()
        sequence_type = params["sequence_type"]
        trigger_mode = params["sequence_parameters"]["trigger_mode"]
        if t not in [1, 4] and sequence_type == SequenceType.TRIGGER:
            assert trigger_mode == types[1]
        else:
            assert trigger_mode == types[t]

    @rule(t=st.integers(-1, 5))
    def change_trigger_by_string(self, t):
        types = {
            -1: "None",
            0: None,
            1: "Send Trigger",
            2: "External Trigger",
            3: "Receive Trigger",
            4: "Send and Receive Trigger",
            5: "ZSync Trigger",
        }
        self.sequenceProgram.set_params(trigger_mode=types[t])
        params = self.sequenceProgram.list_params()
        sequence_type = params["sequence_type"]
        trigger_mode = params["sequence_parameters"]["trigger_mode"]
        if t not in [1, 4] and sequence_type == SequenceType.TRIGGER:
            assert trigger_mode.value == types[1]
        elif t == -1:
            assert trigger_mode.value is None
        else:
            assert trigger_mode.value == types[t]

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

    @rule(i=st.integers(-10, 1000))
    def change_trigger_samples(self, i):
        granularity = 16
        minimum_length = 32
        if i % granularity != 0 or i < minimum_length:
            with pytest.raises(ValueError):
                self.sequenceProgram.set_params(trigger_samples=i)
        else:
            self.sequenceProgram.set_params(trigger_samples=i)
            params = self.sequenceProgram.list_params()
            assert params["sequence_parameters"]["trigger_samples"] == i

    @rule(i=st.integers(-10, 100))
    def change_latency_adjustment(self, i):
        if i < 0:
            with pytest.raises(ValueError):
                self.sequenceProgram.set_params(latency_adjustment=i)
        else:
            self.sequenceProgram.set_params(latency_adjustment=i)
            params = self.sequenceProgram.list_params()
            target = params["sequence_parameters"]["target"]
            trigger_mode = params["sequence_parameters"]["trigger_mode"]
            latency_adjustment = params["sequence_parameters"]["latency_adjustment"]
            latency_cycles = params["sequence_parameters"]["latency_cycles"]
            assert latency_adjustment == i
            if target in [DeviceTypes.HDAWG]:
                if trigger_mode in [TriggerMode.ZSYNC_TRIGGER]:
                    assert latency_cycles == 0 + latency_adjustment
                else:
                    assert latency_cycles == 27 + latency_adjustment
            elif target in [DeviceTypes.UHFLI, DeviceTypes.UHFQA]:
                assert latency_cycles == 0 + latency_adjustment

    @rule(i=st.booleans())
    def change_reset_phase(self, i):
        self.sequenceProgram.set_params(reset_phase=i)
        params = self.sequenceProgram.list_params()
        sequence_type = params["sequence_type"]
        reset_phase = params["sequence_parameters"]["reset_phase"]
        if sequence_type == SequenceType.PULSED_SPEC:
            assert reset_phase is True
        else:
            assert reset_phase is i

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
        sequence_type = self.sequenceProgram.sequence_type
        assert str(sequence_type.value) in sequence


TestPrograms = SequenceProgramMachine.TestCase
