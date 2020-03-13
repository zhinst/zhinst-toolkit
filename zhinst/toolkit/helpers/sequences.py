# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .seq_commands import SeqCommand

import textwrap
import attr
import numpy as np
from pathlib import Path


def is_positive(self, attribute, value):
    if value < 0:
        raise ValueError("Must be positive!")


def amp_smaller_1(self, attribute, value):
    if np.max(np.abs(value)) > 1.0:
        raise ValueError("Amplitude cannot be larger than 1.0!")


@attr.s
class Sequence(object):
    target = attr.ib(default="hdawg", validator=attr.validators.in_(["hdawg", "uhfqa"]))
    clock_rate = attr.ib(default=2.4e9, validator=is_positive)
    period = attr.ib(default=100e-6, validator=is_positive)
    trigger_mode = attr.ib(
        default="None",
        validator=attr.validators.in_(["None", "Send Trigger", "External Trigger"]),
    )
    repetitions = attr.ib(default=1, converter=int, validator=is_positive)
    alignment = attr.ib(
        default="End with Trigger",
        validator=attr.validators.in_(["End with Trigger", "Start with Trigger"]),
    )
    n_HW_loop = attr.ib(default=1, converter=int, validator=is_positive)
    dead_time = attr.ib(default=5e-6, validator=is_positive)
    trigger_delay = attr.ib(default=0)
    latency = attr.ib(default=160e-9, validator=is_positive)
    trigger_cmd_1 = attr.ib(default="//")
    trigger_cmd_2 = attr.ib(default="//")
    wait_cycles = attr.ib(default=0)
    dead_cycles = attr.ib(default=0)
    reset_phase = attr.ib(default=False)

    def set(self, **settings):
        for key in settings:
            if hasattr(self, key):
                setattr(self, key, settings[key])
        self.update_params()
        self.check_attributes()

    def get(self):
        self.update_params()
        self.check_attributes()
        self.write_sequence()
        return self.sequence

    def write_sequence(self):
        self.sequence = None

    def update_params(self):
        if self.trigger_mode == "None":
            self.trigger_cmd_1 = SeqCommand.comment_line()
            self.trigger_cmd_2 = SeqCommand.comment_line()
            self.dead_cycles = 0
        elif self.trigger_mode == "Send Trigger":
            self.trigger_cmd_1 = SeqCommand.trigger(1)
            self.trigger_cmd_2 = SeqCommand.trigger(0)
            self.dead_cycles = self.time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.trigger_cmd_1 = SeqCommand.wait_dig_trigger(
                index=int(self.target == "uhfqa")
            )
            self.trigger_cmd_2 = SeqCommand.comment_line()
            self.dead_cycles = 0

    def time_to_cycles(self, time, wait_time=True):
        if wait_time:
            return int(time * self.clock_rate / 8)
        else:
            return int(time * self.clock_rate)

    def get_gauss_params(self, width, truncation):
        gauss_length = (
            self.time_to_cycles(2 * truncation * width, wait_time=False) // 16 * 16
        )
        gauss_pos = int(gauss_length / 2)
        gauss_width = self.time_to_cycles(width, wait_time=False)
        self.gauss_params = [gauss_length, gauss_pos, gauss_width]

    def check_attributes(self):
        if (self.period - self.dead_time - self.latency + self.trigger_delay) < 0:
            raise ValueError("Wait time cannot be negative!")

    def __setattr__(self, name, value) -> None:
        """Call the validator when we set the field (by default it only runs on __init__)"""
        for attribute in [
            a for a in getattr(self.__class__, "__attrs_attrs__", []) if a.name == name
        ]:
            if attribute.type is not None:
                if isinstance(value, attribute.type) is False:
                    raise TypeError(
                        f"{self.__class__.__name__}.{attribute.name} cannot set {value} because it is not a {attribute.type.__name__}"
                    )
            if attribute.validator is not None:
                attribute.validator(self, attribute, value)
        super().__setattr__(name, value)


@attr.s
class SimpleSequence(Sequence):
    buffer_lengths = attr.ib(default=[800], validator=attr.validators.instance_of(list))
    delay_times = attr.ib(default=[0])

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="Simple")
        for i in range(self.n_HW_loop):
            self.sequence += SeqCommand.init_buffer_indexed(self.buffer_lengths[i], i)
        self.sequence += SeqCommand.trigger(0)
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i in range(self.n_HW_loop):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.target == "hdawg" and self.reset_phase:
                self.sequence += SeqCommand.reset_osc_phase()
            if self.alignment == "Start with Trigger":
                temp = self.wait_cycles
            elif self.alignment == "End with Trigger":
                temp = self.wait_cycles - self.buffer_lengths[i] / 8
            self.sequence += SeqCommand.wait(
                temp - self.time_to_cycles(self.delay_times[i])
            )
            self.sequence += self.trigger_cmd_2
            if self.target == "uhfqa":
                self.sequence += SeqCommand.readout_trigger()
            self.sequence += SeqCommand.play_wave_indexed(i)
            self.sequence += SeqCommand.wait_wave()
            if self.trigger_mode != "External Trigger":
                if self.alignment == "Start with Trigger":
                    temp = self.dead_cycles - self.buffer_lengths[i] / 8
                elif self.alignment == "End with Trigger":
                    temp = self.dead_cycles
            else:
                temp = 0
            self.sequence += SeqCommand.wait(
                temp + self.time_to_cycles(self.delay_times[i])
            )
            self.sequence += SeqCommand.new_line()
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        if self.trigger_mode == "None":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "Send Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )
        if len(self.buffer_lengths) != self.n_HW_loop:
            self.n_HW_loop = len(self.buffer_lengths)

        if len(self.buffer_lengths) < len(self.delay_times):
            self.delay_times = self.delay_times[: len(self.buffer_lengths)]
        if len(self.buffer_lengths) > len(self.delay_times):
            n = len(self.buffer_lengths) - len(self.delay_times)
            self.delay_times = np.append(self.delay_times, np.zeros(n))
        if self.target == "uhfqa":
            self.clock_rate = 1.8e9

    def check_attributes(self):
        super().check_attributes()
        if len(self.buffer_lengths) > self.n_HW_loop:
            raise ValueError(
                "Length of list buffer_lengths has to be equal to length of HW loop!"
            )


@attr.s
class RabiSequence(Sequence):
    pulse_amplitudes = attr.ib(default=[1.0], validator=amp_smaller_1)
    pulse_width = attr.ib(default=50e-9, validator=is_positive)
    pulse_truncation = attr.ib(default=3, validator=is_positive)

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="Rabi")
        self.sequence += SeqCommand.init_gauss(self.gauss_params)
        self.sequence += self.trigger_cmd_2
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i, amp in enumerate(self.pulse_amplitudes):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.reset_phase:
                self.sequence += SeqCommand.reset_osc_phase()
            self.sequence += SeqCommand.wait(self.wait_cycles)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave_scaled(amp, amp)
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.pulse_amplitudes)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in ["None", "Send Trigger"]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
            if self.alignment == "End with Trigger":
                self.wait_cycles -= self.gauss_params[0] / 8
            elif self.alignment == "Start with Trigger":
                self.dead_cycles -= self.gauss_params[0] / 8
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )
            if self.alignment == "End with Trigger":
                self.wait_cycles -= self.gauss_params[0] / 8
            elif self.alignment == "Start with Trigger":
                self.dead_cycles = 0

    def check_attributes(self):
        super().check_attributes()
        if (
            self.period - self.dead_time - 2 * self.pulse_width * self.pulse_truncation
        ) < 0:
            raise ValueError("Wait time cannot be negative!")
        if self.n_HW_loop < len(self.pulse_amplitudes):
            raise ValueError(
                "Length of hardware loop too long for number of specified amplitudes!"
            )


@attr.s
class T1Sequence(Sequence):
    pulse_amplitude = attr.ib(default=1, validator=amp_smaller_1)
    pulse_width = attr.ib(default=50e-9, validator=is_positive)
    pulse_truncation = attr.ib(default=3, validator=is_positive)
    delay_times = attr.ib(default=[1e-6])

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="T1")
        self.sequence += SeqCommand.init_gauss_scaled(
            self.pulse_amplitude, self.gauss_params
        )
        self.sequence += self.trigger_cmd_2
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i, t in enumerate([self.time_to_cycles(t) for t in (self.delay_times)]):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.reset_phase:
                self.sequence += SeqCommand.reset_osc_phase()
            self.sequence += SeqCommand.wait(self.wait_cycles - t)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave()
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles + t)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.delay_times)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in ["None", "Send Trigger"]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )
        # if self.alignment == "Start with Trigger":
        #     self.wait_cycles -= self.gauss_params[0] / 8

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - self.gauss_params[0] / self.clock_rate) < 0:
            raise ValueError("Wait time cannot be negative!")
        if self.n_HW_loop > len(self.delay_times):
            raise ValueError(
                "Length of hardware loop too long for number of specified delay times!"
            )


@attr.s
class T2Sequence(T1Sequence):
    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="T2* (Ramsey)")
        self.sequence += SeqCommand.init_gauss_scaled(
            0.5 * self.pulse_amplitude, self.gauss_params
        )
        self.sequence += self.trigger_cmd_2
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i, t in enumerate([self.time_to_cycles(t) for t in (self.delay_times)]):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.reset_phase:
                self.sequence += SeqCommand.reset_osc_phase()
            self.sequence += SeqCommand.wait(self.wait_cycles - t)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave()
            if t > 3:
                self.sequence += SeqCommand.wait(
                    t - 3
                )  # -3 to subtract additional cycles of playWave() ...
            else:
                self.sequence += SeqCommand.wait(t)
            self.sequence += SeqCommand.play_wave()
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()


@attr.s
class ReadoutSequence(Sequence):
    readout_length = attr.ib(default=2e-6, validator=is_positive)
    readout_amplitudes = attr.ib(default=[1])
    readout_frequencies = attr.ib(default=[100e6])
    phase_shifts = attr.ib(default=[0])

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="Readout")
        length = self.time_to_cycles(self.readout_length, wait_time=False) // 16 * 16
        self.sequence += SeqCommand.init_readout_pulse(
            length,
            self.readout_amplitudes,
            self.readout_frequencies,
            self.phase_shifts,
            clk_rate=self.clock_rate,
        )
        self.sequence += SeqCommand.trigger(0)
        self.sequence += SeqCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SeqCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        if self.target == "uhfqa":
            self.sequence += SeqCommand.readout_trigger()
        self.sequence += SeqCommand.play_wave()
        self.sequence += SeqCommand.wait_wave()
        self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        temp = self.period - self.dead_time
        if self.alignment == "End with Trigger":
            temp -= self.readout_length
        elif self.alignment == "Start with Trigger":
            self.dead_cycles = self.time_to_cycles(self.dead_time - self.readout_length)
        if self.trigger_mode == "None":
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == "Send Trigger":
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(
                temp - self.latency + self.trigger_delay
            )
        if self.target == "uhfqa":
            self.clock_rate = 1.8e9
        len_f = len(self.readout_frequencies)
        len_a = len(self.readout_amplitudes)
        len_p = len(self.phase_shifts)
        if len_a < len_f:
            self.readout_amplitudes += [1] * (len_f - len_a)
        if len_a > len_f:
            self.readout_amplitudes = self.readout_amplitudes[:len_f]
        if len_p < len_f:
            self.phase_shifts += [0] * (len_f - len_p)
        if len_p > len_f:
            self.phase_shifts = self.phase_shifts[:len_f]


@attr.s
class PulsedSpectroscopySequence(Sequence):
    pulse_length = attr.ib(default=2e-6, validator=is_positive)
    pulse_amplitude = attr.ib(default=1)

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="Pulsed Spectroscopy")
        length = self.time_to_cycles(self.pulse_length, wait_time=False) // 16 * 16
        self.sequence += SeqCommand.init_ones(self.pulse_amplitude, length)
        self.sequence += SeqCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SeqCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        self.sequence += SeqCommand.readout_trigger()
        self.sequence += SeqCommand.play_wave()
        self.sequence += SeqCommand.wait_wave()
        self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.target = "uhfqa"
        temp = self.period - self.dead_time
        if self.alignment == "End with Trigger":
            temp -= self.pulse_length
        elif self.alignment == "Start with Trigger":
            self.dead_cycles = self.time_to_cycles(self.dead_time - self.pulse_length)
        if self.trigger_mode == "None":
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == "Send Trigger":
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(
                temp - self.latency + self.trigger_delay
            )
        if self.target == "uhfqa":
            self.clock_rate = 1.8e9


@attr.s
class CWSpectroscopySequence(Sequence):
    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="CW Spectroscopy")
        self.sequence += SeqCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SeqCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        self.sequence += SeqCommand.readout_trigger()
        self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        if self.trigger_mode == "None":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "Send Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )


@attr.s
class CustomSequence(Sequence):
    path = attr.ib(default="")
    program = attr.ib(default="")
    custom_params = attr.ib(default=[])

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="Custom")
        self.sequence += f"// from file: {self.path}\n\n"
        self.sequence += self.program

    def update_params(self):
        if self.path:
            self.program = Path(self.path).read_text()
        for i, p in enumerate(self.custom_params):
            self.program = self.program.replace(f"$param{i+1}$", str(p))

    def check_attributes(self):
        if self.path:
            p = Path(self.path)
            if p.suffix != ".seqc":
                raise ValueError("Specified file is not a .seqc file!")
