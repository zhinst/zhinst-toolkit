# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import textwrap
import attr
import numpy as np
from pathlib import Path

from .sequence_commands import SequenceCommand
from .utils import SequenceType, TriggerMode, Alignment
from zhinst.toolkit.interface import DeviceTypes


def is_positive(self, attribute, value):
    if value < 0:
        raise ValueError("Must be positive!")


def amp_smaller_1(self, attribute, value):
    if np.max(np.abs(value)) > 1.0:
        raise ValueError("Amplitude cannot be larger than 1.0!")


@attr.s
class Sequence(object):
    """Base class for an AWG sequence to be programmed on a :class:`AWGCore` .
    
    Attributes:
        period (double): Period in seconds at which the experiment is repeated.
        trigger_mode (str or :class:`TriggerMode` enum): The trigger mode of the 
            sequence, i.e if the AWG Core is used to send out the triger signal 
            (*'Send Triger'* or :class:`TriggerMode.SEND_TRIGGER`) or to wait 
            for an external trigger signal (*'External Triger'* or 
            :class:`TriggerMode.EXTERNAL_TRIGGER`). (default: 
            :class:`TriggerMode.NONE`) 
        repetitions (int): The number of repetitions of the experiment.
        alignment (str): The alignment of the played waveform with the trigger 
            signal, i.e. if the waveform should start with the trigger (or the 
            time origin `t=0` of the sequence). Waveforms can either *'Start 
            with Trigger'* (:class:`Alignment.START_WITH_TRIGGER`) or *'End with 
            Trigger'* (:class:`Alignment.END_WITH_TRIGGER`).
        dead_time (double): The `dead time` of a sequence is the time in seconds 
            after the time origin of the sequence before the next  trigger 
            signal is sent / expected. This time defines the maximum length of a 
            waveform played after the time origin, otherwise triggers can be 
            missed. (default: 5 us)
        trigger_delay (double): The `trigger delay` is an addittional delay in 
            seconds that shifts the time origin `t=0` with respect to the 
            trigger signal. (default: 0)
        latency (double): The `latency` is a time in seconds that compensated 
            for different trigger latencies of different instruments. It works 
            as a constant `trigger_delay`.  
        reset_phase (bool): A flag that specifies if the phase of the modulation 
            oscillator should be reset to 0 for every repetition of the 
            experiment before the waveform is played. This value only applies 
            for AWG Cores of the HDAWG when IQ Modulation is enabled.
    
    """

    target = attr.ib(
        default=DeviceTypes.HDAWG,
        validator=attr.validators.in_(
            [DeviceTypes.HDAWG, DeviceTypes.UHFQA, DeviceTypes.UHFLI]
        ),
    )
    clock_rate = attr.ib(default=2.4e9, validator=is_positive)
    period = attr.ib(default=100e-6, validator=is_positive)
    trigger_mode = attr.ib(
        default=TriggerMode.SEND_TRIGGER,
        converter=lambda m: TriggerMode.NONE if m == "None" else TriggerMode(m),
    )
    repetitions = attr.ib(default=1)
    alignment = attr.ib(
        default=Alignment.END_WITH_TRIGGER, converter=lambda a: Alignment(a)
    )
    n_HW_loop = attr.ib(default=1, converter=int, validator=is_positive)
    dead_time = attr.ib(default=5e-6, validator=is_positive)
    trigger_delay = attr.ib(default=0)
    latency = attr.ib(default=160e-9, validator=is_positive)
    trigger_cmd_1 = attr.ib(default="//")
    trigger_cmd_2 = attr.ib(default="//")
    wait_cycles = attr.ib(default=0)
    dead_cycles = attr.ib(default=1500)  # 5 us by default
    reset_phase = attr.ib(default=False)

    def set(self, **settings):
        """Sets attributes, updates related attributes and checks attributes."""
        for key in settings:
            if hasattr(self, key):
                setattr(self, key, settings[key])
        self.update_params()
        self.check_attributes()

    def get(self):
        """Updates and checks attributes, writes and returns the sequence program."""
        self.update_params()
        self.check_attributes()
        self.write_sequence()
        return self.sequence

    def write_sequence(self):
        """To be overridden by children classes."""
        self.sequence = None

    def update_params(self):
        """Update interrelated parameters."""
        if self.trigger_mode == TriggerMode.NONE:
            self.trigger_cmd_1 = SequenceCommand.comment_line()
            self.trigger_cmd_2 = SequenceCommand.comment_line()
            self.dead_cycles = self.time_to_cycles(self.dead_time)
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.trigger_cmd_1 = SequenceCommand.trigger(1)
            self.trigger_cmd_2 = SequenceCommand.trigger(0)
            self.dead_cycles = self.time_to_cycles(self.dead_time)
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
            self.trigger_cmd_1 = SequenceCommand.wait_dig_trigger(
                index=int(self.target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI])
            )
            self.trigger_cmd_2 = SequenceCommand.comment_line()
            self.dead_cycles = 0

    def time_to_cycles(self, time, wait_time=True):
        """Helper method to convert time to FPGA clock cycles."""
        if wait_time:
            return int(time * self.clock_rate / 8)
        else:
            return int(time * self.clock_rate)

    def get_gauss_params(self, width, truncation):
        """Calculates the attribute `gauss_params` from width and truncation.
        
        Arguments:
            width (double): width in seconds of the gaussian pulse
            truncation (double): the gaussian pulse shape will be truncated 
                at `truncation * width` 
        
        """
        gauss_length = (
            self.time_to_cycles(2 * truncation * width, wait_time=False) // 16 * 16
        )
        gauss_pos = int(gauss_length / 2)
        gauss_width = self.time_to_cycles(width, wait_time=False)
        self.gauss_params = [gauss_length, gauss_pos, gauss_width]

    def check_attributes(self):
        """Performs sanity checks on the sequence parameters."""
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
            if attribute.converter is not None:
                value = attribute.converter(value)
            if attribute.validator is not None:
                attribute.validator(self, attribute, value)
        super().__setattr__(name, value)


@attr.s
class SimpleSequence(Sequence):
    """Sequence for *simple* playback of waveform arrays.

    Initializes placeholders (`randomUniform(...)`) of the correct length for 
    the waveforms in the queue of the AWG Core. The data of the waveform 
    placeholders is then replaced in memory when uploading the waveform using 
    `upload_waveforms()`. The waveforms are played sequentially within the main 
    loop of the sequence program.

        >>> awg.set_sequence_params(sequence_type="Simple")
        >>> awg.queue_waveform(np.ones(800), np.oenes(800))
        >>> awg.compile_and_upload_waveforms()
        >>> ...
    
    Attributes:
        buffer_lengths (list): A list of integers with the required lengths of 
            the waveform buffers. These values will be taken from the waveforms
            in the queue of the AWG Core.
        delay_times (list): A list of delay times for each fo the individual 
            waveform w.r.t. the time origin of the period. These values will be 
            taken from the waveform queue of the AWG Core.  
    
    """

    buffer_lengths = attr.ib(default=[800], validator=attr.validators.instance_of(list))
    delay_times = attr.ib(default=[0])

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Simple")
        for i in range(self.n_HW_loop):
            self.sequence += SequenceCommand.init_buffer_indexed(
                self.buffer_lengths[i], i
            )
        self.sequence += SequenceCommand.trigger(0)
        self.sequence += SequenceCommand.repeat(self.repetitions)
        for i in range(self.n_HW_loop):
            self.sequence += SequenceCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.target == DeviceTypes.HDAWG and self.reset_phase:
                self.sequence += SequenceCommand.reset_osc_phase()
            if self.alignment == Alignment.START_WITH_TRIGGER:
                temp = self.wait_cycles
            elif self.alignment == Alignment.END_WITH_TRIGGER:
                temp = self.wait_cycles - self.buffer_lengths[i] / 8
            self.sequence += SequenceCommand.wait(
                temp - self.time_to_cycles(self.delay_times[i])
            )
            self.sequence += self.trigger_cmd_2
            if self.target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI]:
                self.sequence += SequenceCommand.readout_trigger()
            self.sequence += SequenceCommand.play_wave_indexed(i)
            self.sequence += SequenceCommand.wait_wave()
            if self.trigger_mode == TriggerMode.SEND_TRIGGER:
                if self.alignment == Alignment.START_WITH_TRIGGER:
                    temp = self.dead_cycles - self.buffer_lengths[i] / 8
                elif self.alignment == Alignment.END_WITH_TRIGGER:
                    temp = self.dead_cycles
            else:
                temp = 0
            self.sequence += SequenceCommand.wait(
                temp + self.time_to_cycles(self.delay_times[i])
            )
            self.sequence += SequenceCommand.new_line()
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        if self.trigger_mode == TriggerMode.NONE:
            self.wait_cycles = self.time_to_cycles(self.period)
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
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
        if self.target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI]:
            self.clock_rate = 1.8e9

    def check_attributes(self):
        super().check_attributes()
        if len(self.buffer_lengths) > self.n_HW_loop:
            raise ValueError(
                "Length of list buffer_lengths has to be equal to length of HW loop!"
            )


@attr.s
class TriggerSequence(Sequence):
    """Predefined sequence for *Master Trigger*.
    
    This sequence does not play any waveforms but only sends the trigger signal 
    at the start of every period. The `trigger_mode` parameter will be 
    overwritten to be *'Send Trigger'*. The trigger signal will be played on the 
    *Mark* output of the lower channel.

        >>> awg.set_sequence_params(
        >>>     sequence_type="Trigger",
        >>>     period=50e-6,
        >>>     repetitions=1e3,
        >>> )
    
    """

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Master Trigger")
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SequenceCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.wait(self.dead_cycles)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        self.trigger_mode = TriggerMode.SEND_TRIGGER
        self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        super().update_params()

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time) < 0:
            raise ValueError("Wait time cannot be negative!")


@attr.s
class RabiSequence(Sequence):
    """Predefined *Rabi Sequence*.
    
    This sequence plays a Gaussian pulse with width `pulse_width` and varies its 
    amplitude. The values for the amplitude sweep are defined in the array 
    parameter `pulse_amplitudes`. For each value in the array, one pulse of that 
    amplitude is played in the main loop of the seuence program in the same 
    order as in the array.

        >>> awg.set_sequence_params(
        >>>     sequence_type="Rabi",
        >>>     pulse_width=50e-9,
        >>>     pulse_amplitudes=np.linspace(0, 1.0, 101),    
        >>> )

    Attributes:
        pulse_amplitudes (list): A list of pulse amplitudes for each point in 
            the Rabi sequence. The pulse amplitudes have to be within -1.0 and 
            1.0.
        pulse_width (double): The width of the gaussian pulse (sigma) in 
            seconds.
        pulse_truncation (double): The truncation of the gaussian pulse as 
            multiples of the width. 

    """

    pulse_amplitudes = attr.ib(default=[1.0], validator=amp_smaller_1)
    pulse_width = attr.ib(default=50e-9, validator=is_positive)
    pulse_truncation = attr.ib(default=3, validator=is_positive)

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Rabi")
        self.sequence += SequenceCommand.init_gauss(self.gauss_params)
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.repeat(self.repetitions)
        for i, amp in enumerate(self.pulse_amplitudes):
            self.sequence += SequenceCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.reset_phase:
                self.sequence += SequenceCommand.reset_osc_phase()
            self.sequence += SequenceCommand.wait(self.wait_cycles)
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.play_wave_scaled(amp, amp)
            self.sequence += SequenceCommand.wait_wave()
            self.sequence += SequenceCommand.wait(self.dead_cycles)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.pulse_amplitudes)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode == TriggerMode.NONE:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
            self.dead_cycles = (
                self.time_to_cycles(self.dead_time) - self.gauss_params[0] / 8
            )
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
            if self.alignment == Alignment.END_WITH_TRIGGER:
                self.wait_cycles -= self.gauss_params[0] / 8
            elif self.alignment == Alignment.START_WITH_TRIGGER:
                self.dead_cycles -= self.gauss_params[0] / 8
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )
            if self.alignment == Alignment.END_WITH_TRIGGER:
                self.wait_cycles -= self.gauss_params[0] / 8
            elif self.alignment == Alignment.START_WITH_TRIGGER:
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
    """Predefined *T1 Sequence*.
    
    This sequence plays a Gaussian pulse with width `pulse_width` and amplitude
    `pulse_amplitude`. The shift of the waveform with respect to the period's 
    time origin `t=0` is defined in the array parameter `time_delays`. For each 
    value in the array, one pulse is shifted by the given value (in seconds) 
    forward in time is played in the main loop of the seuence program.

        >>> awg.set_sequence_params(
        >>>     sequence_type="T1",
        >>>     pulse_amplitude=0.876,
        >>>     pulse_width=50e-9,
        >>>     delay_times=np.linspace(0.1e-6, 10e-6, 100),    
        >>> )

    Attributes:
        pulse_amplitude (double): The amplitude of the Gaussian pulse 
            (pi-pulse). Must be between -1.0 and 1.0.
        pulse_width (double): The width of the gaussian pulse (sigma) in 
            seconds.
        pulse_truncation (double): The truncation of the gaussian pulse as 
            multiples of the width. 
        delay_times (array): The time shifts in seconds of the waveforms forward 
            in time with respect to the period's time origin `t=0`.
    
    """

    pulse_amplitude = attr.ib(default=1, validator=amp_smaller_1)
    pulse_width = attr.ib(default=50e-9, validator=is_positive)
    pulse_truncation = attr.ib(default=3, validator=is_positive)
    delay_times = attr.ib(default=[1e-6])

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="T1")
        self.sequence += SequenceCommand.init_gauss_scaled(
            self.pulse_amplitude, self.gauss_params
        )
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.repeat(self.repetitions)
        for i, t in enumerate([self.time_to_cycles(t) for t in (self.delay_times)]):
            self.sequence += SequenceCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.reset_phase:
                self.sequence += SequenceCommand.reset_osc_phase()
            self.sequence += SequenceCommand.wait(self.wait_cycles - t)
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.play_wave()
            self.sequence += SequenceCommand.wait_wave()
            self.sequence += SequenceCommand.wait(self.dead_cycles + t)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.delay_times)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in [TriggerMode.NONE, TriggerMode.SEND_TRIGGER]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )

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
    """Predefined *T2 Ramsey* sequence.
    
    This sequence plays *two* Gaussian pulses with width `pulse_width` and 
    amplitude 1/2 * `pulse_amplitude`. The shift between the  waveforms is defined 
    in the array parameter `time_delays`. For each value in the array, the first
    pulse is shifted forward in time by the given value (in seconds) before the
    second pulse is played.

        >>> awg.set_sequence_params(
        >>>     sequence_type="T1",
        >>>     pulse_amplitude=0.876,
        >>>     pulse_width=50e-9,
        >>>     delay_times=np.linspace(0.1e-6, 10e-6, 100),    
        >>> )

    Attributes:
        pulse_amplitude (double): Twice the amplitude of the Gaussian pulse 
            (pi-half pulse). Must be between -1.0 and 1.0.
        pulse_width (double): The width of the gaussian pulse (sigma) in 
            seconds.
        pulse_truncation (double): The truncation of the gaussian pulse as 
            multiples of the width. 
        delay_times (array): The time shifts in seconds of the waveforms forward 
            in time with respect to the period's time origin `t=0`.
    
    """

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="T2* (Ramsey)")
        self.sequence += SequenceCommand.init_gauss_scaled(
            0.5 * self.pulse_amplitude, self.gauss_params
        )
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.repeat(self.repetitions)
        for i, t in enumerate([self.time_to_cycles(t) for t in (self.delay_times)]):
            self.sequence += SequenceCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.reset_phase:
                self.sequence += SequenceCommand.reset_osc_phase()
            self.sequence += SequenceCommand.wait(self.wait_cycles - t)
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.play_wave()
            if t > 3:
                self.sequence += SequenceCommand.wait(
                    t - 3
                )  # -3 to subtract additional cycles of playWave()
            else:
                self.sequence += SequenceCommand.wait(t)
            self.sequence += SequenceCommand.play_wave()
            self.sequence += SequenceCommand.wait_wave()
            self.sequence += SequenceCommand.wait(self.dead_cycles)
        self.sequence += SequenceCommand.close_bracket()


@attr.s
class ReadoutSequence(Sequence):
    """Predefined sequence for *Multiplexed Qubit Readout*.
    
    The *Readout* sequence is designed for multiplexed qubit readout. It is made 
    to work together with the `Readout Channels` of the *UHFQA*. The sequence 
    generates a readout pulse as the sum of readout tones at different readout 
    frequencies. The readout frequencies are given in the list parameter 
    `readout_frequencies`, their amplitudes in `readout_amplitudes`. If the 
    *Readout* sequence is configured, the *integration mode* is automatically 
    set to *Standard* (weighted integration). 

    For the *UHFQA* the values for *readout frequencies* and *readout 
    amplitudes* can be taken from the respective *Readout Channel*. If the AWG 
    Core is configured to use the *Readout* sequence, upon compilation the 
    sequence takes the values from *all enabled channels*. This ensures that for 
    all channels for which a readout tone is generated, the weighted integration 
    is also a demodulation at that readout frequency. The transfer of the 
    corresponding values from channels to the sequence program is done before 
    compilation or manually using `update_readout_params()`. 

        >>> frequencies = [34e6, 56e6, 78e6, 90e6]
        >>> amplitudes = [0.4, 0.5, 0.6, 0.7]
        >>> for i, ch in enumerate(uhfqa.channels[:4]):
        >>>     ch.enable()
        >>>     ch.readout_frequency(frequencies[i])
        >>>     ch.readout_amplitude(amplitudes[i])
        >>>
        >>> uhfqa.awg.set_sequence_params(
        >>>     sequence_type="Readout",
        >>>     readout_length=1e-6,
        >>> )
        >>> uhfqa.awg.update_readout_params()
        >>> uhfqa.awg
        qa: <zhinst.toolkit.control.drivers.uhfqa.AWG object at 0x000001BA34D978D0>
            parent  : <zhinst.toolkit.control.drivers.uhfqa.UHFQA object at 0x000001BA34D97B38>
            index   : 0
            sequence:
                type: Readout
                    ('target', <DeviceTypes.UHFQA: 'uhfqa'>)
                    ('clock_rate', 1800000000.0)
                    ('period', 0.0001)
                    ('trigger_mode', 'None')
                    ('repetitions', 1)
                    ('alignment', 'End with Trigger')
                    ...
                    ('readout_length', 2e-06)
                    ('readout_amplitudes', [0.4, 0.5, 0.6, 0.7])
                    ('readout_frequencies', [34000000.0, 56000000.0, 78000000.0, 90000000.0])
                    ('phase_shifts', [0, 0, 0, 0])

    Attributes:
        readout_length (double): The duration in seconds of the readout pulse. 
            Note that the maximum integration time for weighted integration is
            4096 samples or roughly 2.3 us. (default: 2 us) 
        readout_freqencies (list): A list of readout frequencies in Hz. These 
            values are typically taken from the *Readout Channels* of the 
            *UHFQA*.
        readout_amplitudes (list): A list of readout amplitudes (-1.0 to 1.0). 
            These values are typically taken from the *Readout Channels* of the 
            *UHFQA*. Note that the amplitude of each tone is always divided by 
            the number of tones.
        phase_shifts (list): A list of additional phase shifts (in degrees) 
            between the generated I and Q quadratures of each individual readout 
            tone.
    
    """

    readout_length = attr.ib(default=2e-6, validator=is_positive)
    readout_amplitudes = attr.ib(default=[1])
    readout_frequencies = attr.ib(default=[100e6])
    phase_shifts = attr.ib(default=[0])

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Readout")
        length = self.time_to_cycles(self.readout_length, wait_time=False) // 16 * 16
        self.sequence += SequenceCommand.init_readout_pulse(
            length,
            self.readout_amplitudes,
            self.readout_frequencies,
            self.phase_shifts,
            clk_rate=self.clock_rate,
        )
        self.sequence += SequenceCommand.trigger(0)
        self.sequence += SequenceCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SequenceCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        if self.target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI]:
            self.sequence += SequenceCommand.readout_trigger()
        self.sequence += SequenceCommand.play_wave()
        self.sequence += SequenceCommand.wait_wave()
        self.sequence += SequenceCommand.wait(self.dead_cycles)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        temp = self.period - self.dead_time
        if self.alignment == Alignment.END_WITH_TRIGGER:
            temp -= self.readout_length
        elif self.alignment == Alignment.START_WITH_TRIGGER:
            self.dead_cycles = self.time_to_cycles(self.dead_time - self.readout_length)
        if self.trigger_mode == TriggerMode.NONE:
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
            self.wait_cycles = self.time_to_cycles(
                temp - self.latency + self.trigger_delay
            )
        if self.target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI]:
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
    """Predefined Sequence for Pulsed Spectroscopy.
    
    This sequence plays a rectangular pulse of duration `pulse_length` (in 
    seconds). When this sequence is configured, the AWG output modulation of the 
    *UHFQA* is enabled and the two output channels are modualted with the *sine*
    and *cosine* of the internal oscillator. The oscillators frequency can be 
    set with the *Parameter* `uhfqa.nodetree.osc.freq`. 
    
    Similarly, the *integration mode* of the *UHFQA* is set to *Spectroscopy* to 
    demodulate the input signals with the *sine* and *cosine* of the same 
    internal oscillator. Note that when modulating the AWG output, the value for 
    *integration time* has to be set to at least as long as the *pulse duration* 
    of the modulated pulse.

        >>> awg.set_sequence_params(
        >>>     sequence_type="Pulsed Spectroscopy",
        >>>     pulse_length=5e-6,
        >>>     pulse_amplitude=0.567,    
        >>> )  

    Attributes:
        pulse_length (double): The duration of the spectroscopy pulse in 
            seconds.  
        pulse_amplitude (double): The amplitude of the generated rectangular 
            pulse.
    
    """

    pulse_length = attr.ib(default=2e-6, validator=is_positive)
    pulse_amplitude = attr.ib(default=1)

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(
            sequence_type="Pulsed Spectroscopy"
        )
        length = self.time_to_cycles(self.pulse_length, wait_time=False) // 16 * 16
        self.sequence += SequenceCommand.init_ones(self.pulse_amplitude, length)
        self.sequence += SequenceCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SequenceCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.readout_trigger()
        self.sequence += SequenceCommand.play_wave()
        self.sequence += SequenceCommand.wait_wave()
        self.sequence += SequenceCommand.wait(self.dead_cycles)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.target = DeviceTypes.UHFQA
        temp = self.period - self.dead_time
        if self.alignment == Alignment.END_WITH_TRIGGER:
            temp -= self.pulse_length
        elif self.alignment == Alignment.START_WITH_TRIGGER:
            self.dead_cycles = self.time_to_cycles(self.dead_time - self.pulse_length)
        if self.trigger_mode == TriggerMode.NONE:
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.wait_cycles = self.time_to_cycles(temp)
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
            self.wait_cycles = self.time_to_cycles(
                temp - self.latency + self.trigger_delay
            )
        if self.target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI]:
            self.clock_rate = 1.8e9


@attr.s
class CWSpectroscopySequence(Sequence):
    """Predefined sequence for Continuous-Wave Spectroscopy.

    The sequence configures the direct output of the oscillator signal. There 
    are no actual waveforms payed within the seuqence program, however, the data 
    acquisition of the QA Results is triggered.

    """

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="CW Spectroscopy")
        self.sequence += SequenceCommand.repeat(self.repetitions)
        self.sequence += self.trigger_cmd_1
        self.sequence += SequenceCommand.wait(self.wait_cycles)
        self.sequence += self.trigger_cmd_2
        self.sequence += SequenceCommand.readout_trigger()
        self.sequence += SequenceCommand.wait(self.dead_cycles)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        if self.trigger_mode == TriggerMode.NONE:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == TriggerMode.EXTERNAL_TRIGGER:
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )


@attr.s
class CustomSequence(Sequence):
    """A *Custom Sequence* for compiling an existing `.seqC` program.
    
    The *Custom Sequence* allows the user to specify the file path to an 
    existing `.seqC` program. It needs to be located in the folder
    *".../Zurich Instruments/LabOne/WebServer/awg/src"*. 

    Additionally, the *Custom Sequence* gives the user the ability to define 
    variable placeholders in their `.seqC` program. So parameter `custom_params` 
    expects a list of values that replace placeholders in the program. The 
    placeholders are specified as special in the format `"$param{i}$"` where `i` 
    is the index of the value in the *custom_params* list. 

        >>> awg.set_sequence_params(
        >>>    sequence_type="Custom",
        >>>    path="...\Zurich Instruments\LabOne\WebServer\awg\src\myProgram.seqC",
        >>>    custom_params=[1000, 99, 1],
        >>> )

    If the specified *'myProgram.seqC'* sequence program has placeholders 
    `"$param0$"`, `"$param1$"`, `"$param2$"`, they will be replaced by `"1000"`, 
    `"99"`, `"1"`.

    Attributes:
        path (str): The file path to a preexisting `.seqC` program.
        custom_params (list): A list of parameter values to replace placeholders 
            in the program.
    
    """

    path = attr.ib(default="")
    program = attr.ib(default="")
    custom_params = attr.ib(default=[])

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Custom")
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
