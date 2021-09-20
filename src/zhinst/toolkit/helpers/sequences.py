# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import textwrap
import attr
import numpy as np
from pathlib import Path
import deprecation

from .sequence_commands import SequenceCommand
from .utils import SequenceType, TriggerMode, Alignment
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
from zhinst.toolkit._version import version as __version__

_logger = LoggerModule(__name__)


def is_greater_equal(min_value):
    """Check if the attribute value is greater than or equal to a minimum value.

    This validator can handle both lists and single element attributes. If it
    is a list, it checks if the element with the smallest value is greater than
    or equal to the specified minimum value.
    """

    def compare(self, attribute, value):
        if type(value) is not list:
            value = [value]
        if np.min(value) < min_value:
            _logger.error(
                f"{attribute.name} cannot be smaller than {min_value}!",
                _logger.ExceptionTypes.ValueError,
            )

    return compare


def is_smaller_equal(max_value):
    """Check if the attribute value is smaller than or equal to a maximum value.

    This validator can handle both lists and single element attributes. If it
    is a list, it checks if the element with the greatest value is smaller than
    or equal to the specified maximum value.
    """

    def compare(self, attribute, value):
        if type(value) is not list:
            value = [value]
        if np.max(value) > max_value:
            _logger.error(
                f"{attribute.name} cannot be greater than {max_value}!",
                _logger.ExceptionTypes.ValueError,
            )

    return compare


def is_multiple(factor):
    """Check if the attribute value is multiple of a certain factor.

    This validator is the most useful for checking if an attribute related
    to waveform length comply with the waveform granularity specification of
    an instrument.

    The validator can handle both lists and single element attributes. If it
    is a list, it checks if each element is multiple of the given factor.
    """

    def compare(self, attribute, value):
        if type(value) is not list:
            value = [value]
        for i in value:
            if i % factor != 0:
                _logger.error(
                    f"{attribute.name} must be multiple of {factor}!",
                    _logger.ExceptionTypes.ValueError,
                )

    return compare


@attr.s
class Sequence(object):
    """Base class for an AWG sequence to be programmed on a :class:`AWGCore` .

    Attributes:
        period (double): Period in seconds at which the experiment is repeated.
        trigger_mode (str or :class:`TriggerMode` enum): The trigger mode of the
            sequence, i.e if the AWG Core is used to send out the triger signal
            (*'Send Triger'* or :class:`TriggerMode.SEND_TRIGGER`), to wait
            for an external trigger signal (*'Receive Triger'* or
            :class:`TriggerMode.RECEIVE_TRIGGER`) or to wait for an external
            signal to send out the triger signal (*'Send and Receive Triger'* or
            :class:`TriggerMode.SEND_AND_RECEIVE_TRIGGER`). (default:
            :class:`TriggerMode.NONE`)
        trigger_samples (int): The duration of the trigger signal sent out by
            the AWG Core. It is given in number of samples. (default: 32)
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
        latency_adjustment (int): In order to compensate for different trigger
            latencies of different instrument types, it is necessary for some
            instruments to wait for certain number of sequencer cycles after
            receiving the trigger. This way, it is possible to align the
            waveforms sent out from different instruments. The attribute
            `latency_adjustment` is an additional latency given as number of
            sequencer cycles that is used to increase the time an instrument
            waits after receiving the trigger signal. (default: 0)
        reset_phase (bool): A flag that specifies if the phase of the modulation
            oscillator should be reset to 0 for every repetition of the
            experiment before the waveform is played.

    """

    target = attr.ib(
        default=DeviceTypes.HDAWG,
        validator=attr.validators.in_(
            [
                DeviceTypes.HDAWG,
                DeviceTypes.UHFQA,
                DeviceTypes.UHFLI,
                DeviceTypes.SHFQA,
                DeviceTypes.SHFSG,
            ]
        ),
    )
    clock_rate = attr.ib(default=2.4e9, validator=is_greater_equal(0))
    period = attr.ib(default=100e-6, validator=is_greater_equal(0))
    trigger_mode = attr.ib(
        default=TriggerMode.SEND_TRIGGER,
        converter=lambda m: TriggerMode.NONE if m == "None" else TriggerMode(m),
    )
    trigger_samples = attr.ib(
        default=32,
        validator=[is_greater_equal(32), is_multiple(16)],
    )
    repetitions = attr.ib(default=1)
    alignment = attr.ib(
        default=Alignment.END_WITH_TRIGGER, converter=lambda a: Alignment(a)
    )
    n_HW_loop = attr.ib(default=1, converter=int, validator=is_greater_equal(0))
    dead_time = attr.ib(default=5e-6, validator=is_greater_equal(0))
    trigger_delay = attr.ib(default=0)
    latency = attr.ib(default=160e-9, validator=is_greater_equal(0))
    latency_cycles = attr.ib(default=27, validator=is_greater_equal(0))
    latency_adjustment = attr.ib(default=0, validator=is_greater_equal(0))
    trigger_cmd_1 = attr.ib(default="//")
    trigger_cmd_2 = attr.ib(default="//")
    trigger_cmd_define = attr.ib(default="//\n")
    trigger_cmd_send = attr.ib(default="//\n")
    trigger_cmd_wait = attr.ib(default="//\n")
    trigger_cmd_latency = attr.ib(default="//\n")
    readout_cmd_trigger = attr.ib(default="//\n")
    osc_cmd_reset = attr.ib(default="//\n")
    wait_cycles = attr.ib(
        default=28500, validator=is_greater_equal(0)
    )  # 95 us by default
    dead_cycles = attr.ib(
        default=1500, validator=is_greater_equal(0)
    )  # 5 us by default
    wait_samples = attr.ib(
        default=228000, validator=is_greater_equal(0)
    )  # 95 us by default (Assuming HDAWG)
    dead_samples = attr.ib(
        default=12000, validator=is_greater_equal(0)
    )  # 5 us by default (Assuming HDAWG)
    reset_phase = attr.ib(default=False)
    ct = list()

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
        self.ct = list()
        self.write_ct()
        return [self.sequence, self.ct]

    def write_sequence(self):
        """Create header for the sequencer program.

        The header displays the sequence type, trigger mode and alignment
        information of the program. Sequence type is temporarily selected as
        `None` here. It will be overwritten by the children classes depending
        on the actual sequence type.

        """
        self.sequence = SequenceCommand.header_info(
            SequenceType.NONE, self.trigger_mode, self.alignment
        )

    def write_ct(self):
        """generate commandtable"""

    def update_params(self):
        """Update interrelated parameters."""
        # Convert wait_time to number of samples
        self.wait_samples = self.time_to_samples(
            self.period - self.dead_time + self.trigger_delay
        )
        # Convert dead_time to number of samples
        self.dead_samples = self.time_to_samples(self.dead_time - self.trigger_delay)
        # Set the correct clock rate, trigger latency compensation
        # and QA trigger command depending on the device type
        if self.target in [DeviceTypes.HDAWG]:
            self.clock_rate = 2.4e9
            if self.trigger_mode in [TriggerMode.ZSYNC_TRIGGER]:
                # Default trigger latency for HDAWG with ZSync trigger
                # = 0 cycles
                self.latency_cycles = 0 + self.latency_adjustment
            else:
                # Default trigger latency for HDAWG with Master trigger
                # = 27 cycles
                self.latency_cycles = 27 + self.latency_adjustment
            # HDAWG has no quantum analyzer
            self.readout_cmd_trigger = SequenceCommand.comment_line()
        elif self.target in [DeviceTypes.UHFLI, DeviceTypes.UHFQA]:
            self.clock_rate = 1.8e9
            # Default trigger latency compensation for UHFQA = 0 cycles
            self.latency_cycles = 0 + self.latency_adjustment
            # UHFLI has no has quantum analyzer, only UHFQA has quantum analyzer
            if self.target in [DeviceTypes.UHFQA]:
                self.readout_cmd_trigger = SequenceCommand.readout_trigger()
            else:
                self.readout_cmd_trigger = SequenceCommand.comment_line()
        elif self.target in [DeviceTypes.SHFSG]:
            self.clock_rate = 2e9
            if self.trigger_mode in [TriggerMode.ZSYNC_TRIGGER]:
                # Default trigger latency for HDAWG with ZSync trigger
                # = 0 cycles
                self.latency_cycles = 0 + self.latency_adjustment
            else:
                # Default trigger latency for HDAWG with Master trigger
                # = 27 cycles
                self.latency_cycles = 27 + self.latency_adjustment
            # HDAWG has no quantum analyzer
            self.readout_cmd_trigger = SequenceCommand.comment_line()
        elif self.target in [DeviceTypes.SHFQA]:
            self.clock_rate = 2e9
        # Set the oscillator phase to 0 if the reset_phase option is on
        if self.reset_phase:
            self.osc_cmd_reset = SequenceCommand.reset_osc_phase()
        else:
            self.osc_cmd_reset = SequenceCommand.comment_line()
        # Set the trigger latency command depending on the `latency_cycles`
        if self.latency_cycles == 0:
            self.trigger_cmd_latency = SequenceCommand.comment_line()
        else:
            # strip '\n' at the end and add an inline comment
            self.trigger_cmd_latency = (
                SequenceCommand.wait(self.latency_cycles).rstrip()
                + SequenceCommand.space()
                + SequenceCommand.inline_comment(
                    f"Wait to compensate for trigger latency"
                )
            )
        # Set the trigger commands depending on the trigger mode
        if self.trigger_mode == TriggerMode.NONE:
            self.trigger_cmd_1 = SequenceCommand.comment_line()
            self.trigger_cmd_2 = SequenceCommand.comment_line()
            self.dead_cycles = self.time_to_cycles(self.dead_time)
            self.trigger_cmd_define = SequenceCommand.comment_line()
            self.trigger_cmd_send = SequenceCommand.comment_line()
            self.trigger_cmd_wait = SequenceCommand.comment_line()
            # No trigger latency compensation in TriggerMode.NONE
            self.trigger_cmd_latency = SequenceCommand.comment_line()
        elif self.trigger_mode == TriggerMode.SEND_AND_RECEIVE_TRIGGER:
            # Define a waveform to send out as trigger
            self.trigger_cmd_define = SequenceCommand.define_trigger(
                self.trigger_samples
            )
            # Wait for an external clock to send out the trigger signal
            # strip '\n' at the end and add an inline comment
            self.trigger_cmd_send = (
                SequenceCommand.wait_dig_trigger(2, self.target).rstrip()
                + SequenceCommand.space()
                + SequenceCommand.inline_comment("Wait for external clock")
                + SequenceCommand.play_trigger()
            )
            # Wait for self triggering
            # strip '\n' at the end and add an inline comment
            self.trigger_cmd_wait = (
                SequenceCommand.wait_dig_trigger(1, self.target).rstrip()
                + SequenceCommand.space()
                + SequenceCommand.inline_comment("Wait for self trigger")
            )
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.trigger_cmd_1 = SequenceCommand.trigger(1)
            self.trigger_cmd_2 = SequenceCommand.trigger(0)
            self.dead_cycles = self.time_to_cycles(self.dead_time)
            # Define a waveform to send out as trigger
            self.trigger_cmd_define = SequenceCommand.define_trigger(
                self.trigger_samples
            )
            # Send out the trigger signal
            self.trigger_cmd_send = (
                SequenceCommand.comment_line() + SequenceCommand.play_trigger()
            )
            # Wait for self triggering
            # strip '\n' at the end and add an inline comment
            self.trigger_cmd_wait = (
                SequenceCommand.wait_dig_trigger(1, self.target).rstrip()
                + SequenceCommand.space()
                + SequenceCommand.inline_comment("Wait for self trigger")
            )
        elif self.trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
        ]:
            self.trigger_cmd_1 = SequenceCommand.wait_dig_trigger(1, self.target)
            self.trigger_cmd_2 = SequenceCommand.comment_line()
            self.dead_cycles = 0
            self.trigger_cmd_define = SequenceCommand.comment_line()
            self.trigger_cmd_send = (
                SequenceCommand.comment_line() + SequenceCommand.comment_line()
            )
            # Wait for external trigger
            self.trigger_cmd_wait = SequenceCommand.wait_dig_trigger(1, self.target)
        elif self.trigger_mode == TriggerMode.ZSYNC_TRIGGER:
            self.trigger_cmd_define = SequenceCommand.comment_line()
            self.trigger_cmd_send = SequenceCommand.comment_line()
            # Wait for ZSYNC trigger
            # strip '\n' at the end and add an inline comment
            self.trigger_cmd_wait = (
                SequenceCommand.wait_zsync_trigger().rstrip()
                + SequenceCommand.space()
                + SequenceCommand.inline_comment("Wait for ZSYNC trigger")
            )

    @deprecation.deprecated(
        deprecated_in="0.2.0",
        current_version=__version__,
        details="Use the time_to_samples function instead",
    )
    def time_to_cycles(self, time):
        """Helper method to convert time to FPGA clock cycles."""
        return int(time * self.clock_rate / 8)

    def time_to_samples(self, time):
        """Helper method to convert time to number of samples."""
        return int(time * self.clock_rate)

    def cycles_to_samples(self, cycles: int):
        """Helper method to convert FPGA clock cycles to number of samples."""
        return cycles * 8

    def samples_to_cycles(self, samples: int):
        """Helper method to convert FPGA clock cycles to number of samples."""
        return int(samples / 8)

    def get_gauss_params(self, width, truncation):
        """Calculates the attribute `gauss_params` from width and truncation.

        Arguments:
            width (double): width in seconds of the gaussian pulse
            truncation (double): the gaussian pulse shape will be truncated
                at `truncation * width`

        """
        gauss_length = self.time_to_samples(2 * truncation * width) // 16 * 16
        gauss_pos = int(gauss_length / 2)
        gauss_width = self.time_to_samples(width)
        self.gauss_params = [gauss_length, gauss_pos, gauss_width]

    def check_attributes(self):
        """Performs sanity checks on the sequence parameters."""
        if (self.period - self.dead_time - self.latency + self.trigger_delay) < 0:
            _logger.error(
                "Wait time cannot be negative!",
                _logger.ExceptionTypes.ValueError,
            )

    def __setattr__(self, name, value) -> None:
        """Call the validator when we set the field (by default it only runs on __init__)"""
        for attribute in [
            a for a in getattr(self.__class__, "__attrs_attrs__", []) if a.name == name
        ]:
            if attribute.type is not None:
                if isinstance(value, attribute.type) is False:
                    _logger.error(
                        f"{self.__class__.__name__}.{attribute.name} cannot set "
                        f"{value} because it is not a {attribute.type.__name__}",
                        _logger.ExceptionTypes.TypeError,
                    )
            if attribute.converter is not None:
                value = attribute.converter(value)
            if attribute.validator is not None:
                attribute.validator(self, attribute, value)
        super().__setattr__(name, value)


@attr.s
class SimpleSequence(Sequence):
    """Sequence for *simple* playback of waveform arrays.

    Initializes placeholders (`placeholder(...)`) of the correct length for
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
    wait_samples_updated = attr.ib(default=[0])
    dead_samples_updated = attr.ib(default=[0])

    def write_sequence(self):
        # Call the method from parent class `Sequence` and then overwrite it
        super().write_sequence()
        # Update the sequence type information in the header
        self.sequence = SequenceCommand.replace_sequence_type(
            self.sequence, SequenceType.SIMPLE
        )
        if self.target in [DeviceTypes.SHFSG]:
            self.sequence += SequenceCommand.inline_comment("Waveform definitions")
            for i in range(self.n_HW_loop):
                self.sequence += SequenceCommand.init_buffer_indexed(
                    self.buffer_lengths[i], i, self.target
                )
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.new_line()
            # Loop over the waveforms and assign indices
            for i in range(self.n_HW_loop):
                self.sequence += SequenceCommand.assign_wave_index(i, self.target)
            self.sequence += SequenceCommand.new_line()
            self.sequence += SequenceCommand.inline_comment("Start main sequence")
            # Start repeat loop in sequencer
            self.sequence += SequenceCommand.repeat(self.repetitions)
            # Loop over the waveforms
            for i in range(self.n_HW_loop):
                self.sequence += SequenceCommand.tab() + SequenceCommand.count_waveform(
                    i, self.n_HW_loop
                )
                # Play the Trigger
                self.sequence += SequenceCommand.tab() + self.trigger_cmd_1
                if self.reset_phase:
                    self.sequence += SequenceCommand.tab() + SequenceCommand.reset_osc_phase()
                self.sequence += SequenceCommand.tab() + SequenceCommand.wait(self.samples_to_cycles(self.wait_samples_updated[i]))
                self.sequence += SequenceCommand.tab() + self.trigger_cmd_2
                # Wait for external trigger (depends on the trigger mode)
                self.sequence += self.trigger_cmd_wait

                # Play the waveforms
                self.sequence += SequenceCommand.tab() + SequenceCommand.play_wave(
                    index=i, target=self.target
                )
                self.sequence += SequenceCommand.tab() + SequenceCommand.play_zero(
                    self.dead_samples_updated[i], self.target
                )
            # Finish repeat loop
            self.sequence += SequenceCommand.close_bracket()
        
        else:
            # Loop over the waveforms and initialize placeholders
            self.sequence += SequenceCommand.inline_comment("Waveform definitions")
            for i in range(self.n_HW_loop):
                self.sequence += SequenceCommand.init_buffer_indexed(
                    self.buffer_lengths[i], i, self.target
                )
            # Define trigger waveform (depends on the trigger mode)
            self.sequence += self.trigger_cmd_define
            self.sequence += SequenceCommand.new_line()
            # Loop over the waveforms and assign indices
            for i in range(self.n_HW_loop):
                self.sequence += SequenceCommand.assign_wave_index(i, self.target)
            self.sequence += SequenceCommand.new_line()
            self.sequence += SequenceCommand.inline_comment("Trigger commands")
            # Send trigger (depends on the trigger mode)
            self.sequence += self.trigger_cmd_send
            # Wait for external trigger (depends on the trigger mode)
            self.sequence += self.trigger_cmd_wait
            # Compensate for trigger latency differences (depends on the device type)
            self.sequence += self.trigger_cmd_latency
            self.sequence += SequenceCommand.new_line()
            self.sequence += SequenceCommand.inline_comment("Start main sequence")
            # Start repeat loop in sequencer
            self.sequence += SequenceCommand.repeat(self.repetitions)
            # Loop over the waveforms
            for i in range(self.n_HW_loop):
                self.sequence += SequenceCommand.tab() + SequenceCommand.count_waveform(
                    i, self.n_HW_loop
                )
                # Play zeros to wait before playing the waveform.
                # (depends on `period`, `dead_time` and alignment options)
                self.sequence += SequenceCommand.tab() + SequenceCommand.play_zero(
                    self.wait_samples_updated[i], self.target
                )
                # Reset oscillator phase (depends on `reset_phase` option)
                self.sequence += SequenceCommand.tab() + self.osc_cmd_reset
                # Play the waveforms
                self.sequence += SequenceCommand.tab() + SequenceCommand.play_wave(
                    index=i, target=self.target
                )
                # Trigger quantum analyzer (depends on the device type)
                self.sequence += SequenceCommand.tab() + self.readout_cmd_trigger
                # Play zeros to wait until end of period.
                # (depends on `dead_time` and alignment options)
                self.sequence += SequenceCommand.tab() + SequenceCommand.play_zero(
                    self.dead_samples_updated[i], self.target
                )
            # Finish repeat loop
            self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        if len(self.buffer_lengths) != self.n_HW_loop:
            self.n_HW_loop = len(self.buffer_lengths)
        if len(self.buffer_lengths) < len(self.delay_times):
            self.delay_times = self.delay_times[: len(self.buffer_lengths)]
        if len(self.buffer_lengths) > len(self.delay_times):
            n = len(self.buffer_lengths) - len(self.delay_times)
            self.delay_times = np.append(self.delay_times, np.zeros(n))
        # Update the number of samples to wait before and after playing the waveform
        # according to the list of delay_times, buffer lengths and alignment option.
        self.wait_samples_updated = [self.wait_samples for i in range(self.n_HW_loop)]
        self.dead_samples_updated = [self.dead_samples for i in range(self.n_HW_loop)]
        for i in range(self.n_HW_loop):
            if self.alignment == Alignment.START_WITH_TRIGGER:
                self.wait_samples_updated[i] += self.delay_times[i]
                self.dead_samples_updated[i] -= (
                    self.delay_times[i] + self.buffer_lengths[i]
                )
            elif self.alignment == Alignment.END_WITH_TRIGGER:
                self.wait_samples_updated[i] += (
                    self.delay_times[i] - self.buffer_lengths[i]
                )
                self.dead_samples_updated[i] -= self.delay_times[i]

    def check_attributes(self):
        super().check_attributes()
        if len(self.buffer_lengths) > self.n_HW_loop:
            _logger.error(
                "Length of list buffer_lengths has to be equal to length of HW loop!",
                _logger.ExceptionTypes.ValueError,
            )


@attr.s
class TriggerSequence(Sequence):
    """Predefined sequence for *Master Trigger*.

    This sequence does not play any waveforms but only sends out the
    trigger signal once at the start of the sequence program.
    The `trigger_mode` parameter must be chosen as *'Send Trigger'* or
    *'Send and Receive Trigger'*. Otherwise, it will automatically be
    overwritten to be *'Send Trigger'*. The trigger signal will be
    played on the AWG core output 1. However, this signal should still
    be manually assigned to the desired *Mark* output in DIO settings by
    selecting `Output 1 Marker 1`.

        >>> awg.set_sequence_params(
        >>>     sequence_type="Trigger",
        >>>     period=50e-6,
        >>>     repetitions=1e3,
        >>> )

    """

    def write_sequence(self):
        # Call the method from parent class `Sequence` and then overwrite it
        super().write_sequence()
        # Update the sequence type information in the header
        self.sequence = SequenceCommand.replace_sequence_type(
            self.sequence, SequenceType.TRIGGER
        )
        # Define trigger waveform
        self.sequence += SequenceCommand.inline_comment("Trigger waveform definition")
        self.sequence += self.trigger_cmd_define
        self.sequence += SequenceCommand.new_line()
        self.sequence += SequenceCommand.inline_comment("Trigger commands")
        # Send trigger (depends on the trigger mode)
        self.sequence += self.trigger_cmd_send.rstrip()  # strip '\n' at the end

    def update_params(self):
        # Set the trigger mode to "Send Trigger" if the selected
        # trigger mode is not correct.
        if self.trigger_mode not in [
            TriggerMode.SEND_TRIGGER,
            TriggerMode.SEND_AND_RECEIVE_TRIGGER,
        ]:
            _logger.warning(
                f"The selected trigger mode {self.trigger_mode.value} does not work "
                f"with Master Trigger sequence. The trigger mode is set to "
                f"{TriggerMode.SEND_TRIGGER.value}."
            )
            self.trigger_mode = TriggerMode.SEND_TRIGGER
        # Call the parent function to update all parameters that depend
        # on the trigger mode after overwiritng the trigger mode above.
        # Note that the parent class should not change the trigger mode.
        super().update_params()

    def check_attributes(self):
        super().check_attributes()


@attr.s
class RabiSequence(Sequence):
    """Predefined *Rabi Sequence*.

    This sequence plays a Gaussian pulse with width `pulse_width` and varies its
    amplitude. The values for the amplitude sweep are defined in the array
    parameter `pulse_amplitudes`. For each value in the array, one pulse of that
    amplitude is played in the main loop of the sequence program in the same
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

    pulse_amplitudes = attr.ib(
        default=[1.0],
        validator=[is_greater_equal(-1.0), is_smaller_equal(1.0)],
    )
    pulse_width = attr.ib(default=50e-9, validator=is_greater_equal(0))
    pulse_truncation = attr.ib(default=3, validator=is_greater_equal(0))

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Rabi")
        if self.target in [DeviceTypes.SHFSG]:
            self.sequence += SequenceCommand.init_gauss(self.gauss_params)
            self.sequence += SequenceCommand.assign_wave_index(
                i=0, indexed=False, amplitude=0.5, target=self.target
            )
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.repeat(self.repetitions)
            self.sequence += SequenceCommand.inline_comment(
                "First pulse with 0 amplitude"
            )
            if self.reset_phase:
                self.sequence += SequenceCommand.reset_osc_phase()
            self.sequence += self.trigger_cmd_1
            self.sequence += SequenceCommand.wait(self.wait_cycles)
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.executeTableEntry(0)
            self.sequence += SequenceCommand.play_zero(
                self.cycles_to_samples(self.dead_cycles)
            )
            self.sequence += SequenceCommand.wait_wave()
            self.sequence += SequenceCommand.repeat(len(self.pulse_amplitudes) - 1)
            self.sequence += SequenceCommand.inline_comment(
                "Increment amplitude each repetition"
            )
            if self.reset_phase:
                self.sequence += SequenceCommand.reset_osc_phase()
            self.sequence += self.trigger_cmd_1
            self.sequence += SequenceCommand.wait(self.wait_cycles)
            self.sequence += self.trigger_cmd_2
            self.sequence += SequenceCommand.executeTableEntry(1)
            self.sequence += SequenceCommand.play_zero(
                self.cycles_to_samples(self.dead_cycles)
            )
            self.sequence += SequenceCommand.wait_wave()
            self.sequence += SequenceCommand.close_bracket()
            self.sequence += SequenceCommand.close_bracket()
        else:

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
                self.sequence += SequenceCommand.play_wave(
                    amplitude=amp, target=self.target
                )
                self.sequence += SequenceCommand.wait_wave()
                self.sequence += SequenceCommand.wait(self.dead_cycles)
            self.sequence += SequenceCommand.close_bracket()

    def write_ct(self):
        """generate the commandtable for the sequence"""
        if self.target in [DeviceTypes.SHFSG]:
            entry = {}
            entry["index"] = 0
            entry["waveform"] = {"index": 0}
            entry["amplitude00"] = {
                "value": self.pulse_amplitudes[0],
                "increment": False,
            }
            entry["amplitude01"] = {
                "value": -self.pulse_amplitudes[0],
                "increment": False,
            }
            entry["amplitude10"] = {
                "value": self.pulse_amplitudes[0],
                "increment": False,
            }
            entry["amplitude11"] = {
                "value": self.pulse_amplitudes[0],
                "increment": False,
            }
            self.ct.append(entry)
            if len(self.pulse_amplitudes) > 1:
                delta =  round(self.pulse_amplitudes[1] - self.pulse_amplitudes[0],9)
                if not all(
                    round(val - self.pulse_amplitudes[idx],9) == delta
                    for idx, val in enumerate(self.pulse_amplitudes[1:])
                ):
                    _logger.error(
                        "Amplitudes needs to be equal spaced for the Rabi Sequence with the SHFSG",
                        _logger.ExceptionTypes.ValueError,
                    )
                entry = {}
                entry["index"] = 1
                entry["waveform"] = {"index": 0}
                entry["amplitude00"] = {"value": delta, "increment": True}
                entry["amplitude01"] = {"value": -delta, "increment": True}
                entry["amplitude10"] = {"value": delta, "increment": True}
                entry["amplitude11"] = {"value": delta, "increment": True}
                self.ct.append(entry)

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.pulse_amplitudes)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode == TriggerMode.NONE:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
            self.dead_cycles = self.time_to_cycles(
                self.dead_time
            ) - self.samples_to_cycles(self.gauss_params[0])
        elif self.trigger_mode == TriggerMode.SEND_TRIGGER:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
            if self.alignment == Alignment.END_WITH_TRIGGER:
                self.wait_cycles -= self.samples_to_cycles(self.gauss_params[0])
            elif self.alignment == Alignment.START_WITH_TRIGGER:
                self.dead_cycles -= self.samples_to_cycles(self.gauss_params[0])
        elif self.trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
        ]:
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )
            if self.alignment == Alignment.END_WITH_TRIGGER:
                self.wait_cycles -= self.samples_to_cycles(self.gauss_params[0])
            elif self.alignment == Alignment.START_WITH_TRIGGER:
                self.dead_cycles = 0

    def check_attributes(self):
        super().check_attributes()
        if (
            self.period - self.dead_time - 2 * self.pulse_width * self.pulse_truncation
        ) < 0:
            _logger.error(
                "Wait time cannot be negative!",
                _logger.ExceptionTypes.ValueError,
            )
        if self.n_HW_loop < len(self.pulse_amplitudes):
            _logger.error(
                "Length of hardware loop too long for number of specified amplitudes!",
                _logger.ExceptionTypes.ValueError,
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

    pulse_amplitude = attr.ib(
        default=1,
        validator=[is_greater_equal(-1.0), is_smaller_equal(1.0)],
    )
    pulse_width = attr.ib(default=50e-9, validator=is_greater_equal(0))
    pulse_truncation = attr.ib(default=3, validator=is_greater_equal(0))
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
            self.sequence += SequenceCommand.play_wave(target=self.target)
            if self.target in [DeviceTypes.SHFSG]:
                self.sequence += SequenceCommand.play_zero(
                    self.cycles_to_samples(self.dead_cycles + t), self.target
                )
                self.sequence += SequenceCommand.wait_wave()
            else:
                self.sequence += SequenceCommand.wait_wave()
                self.sequence += SequenceCommand.wait(self.dead_cycles + t)
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.delay_times)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in [TriggerMode.NONE, TriggerMode.SEND_TRIGGER]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
        ]:
            self.wait_cycles = self.time_to_cycles(
                self.period - self.dead_time - self.latency + self.trigger_delay
            )

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - self.gauss_params[0] / self.clock_rate) < 0:
            _logger.error(
                "Wait time cannot be negative!",
                _logger.ExceptionTypes.ValueError,
            )
        if self.n_HW_loop > len(self.delay_times):
            _logger.error(
                "Length of hardware loop too long for number of specified delay times!",
                _logger.ExceptionTypes.ValueError,
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
        >>>     sequence_type="T2*",
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
            self.sequence += SequenceCommand.play_wave(target=self.target)

            t_real = t - 3 if t > 3 else t
            if self.target in [DeviceTypes.SHFSG]:
                self.sequence += SequenceCommand.play_zero(
                    self.cycles_to_samples(t_real), self.target
                )
            else:
                self.sequence += SequenceCommand.wait(t_real)

            self.sequence += SequenceCommand.play_wave(target=self.target)
            if self.target in [DeviceTypes.SHFSG]:
                self.sequence += SequenceCommand.play_zero(
                    self.cycles_to_samples(self.dead_cycles), self.target
                )
                self.sequence += SequenceCommand.wait_wave()
            else:
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

    readout_length = attr.ib(default=2e-6, validator=is_greater_equal(0))
    readout_amplitudes = attr.ib(default=[1])
    readout_frequencies = attr.ib(default=[100e6])
    phase_shifts = attr.ib(default=[0])

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Readout")
        length = self.time_to_samples(self.readout_length) // 16 * 16
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
        self.sequence += SequenceCommand.play_wave(target=self.target)
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
        elif self.trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
        ]:
            self.wait_cycles = self.time_to_cycles(
                temp - self.latency + self.trigger_delay
            )
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

    This sequence plays a rectangular pulse of duration `pulse_length`
    (in seconds). When this sequence is configured, the AWG output
    modulation of the *UHFQA* is enabled and the two output channels are
    modulated with the *sine* and *cosine* of the internal oscillator.
    The oscillators frequency can be set with the *Parameter*
    `uhfqa.nodetree.osc.freq`.

    In this sequence the sine generators are enabled, so the oscillator
    runs continouosly. Therefore, it is required that the oscillator
    phase is set to zero with the `resetOscPhase` instruction before
    playing the pulse. Therefore, `reset_phase` parameter is set to
    `True`.

    Similarly, the *integration mode* of the *UHFQA* is set to
    *Spectroscopy* to demodulate the input signals with the *sine* and
    *cosine* of the same internal oscillator. Note that when modulating
    the AWG output, the value for *integration time* has to be set to at
    least as long as the *pulse duration* of the modulated pulse.


        >>> awg.set_sequence_params(
        >>>     sequence_type="Pulsed Spectroscopy",
        >>>     trigger_mode="Receive Trigger",
        >>>     pulse_length=5e-6,
        >>>     pulse_amplitude=0.567,
        >>> )

    Attributes:
        pulse_length (double): The duration of the spectroscopy pulse in
            seconds.
        pulse_amplitude (double): The amplitude of the generated
            rectangular pulse.

    """

    pulse_length = attr.ib(default=2e-6, validator=is_greater_equal(0))
    pulse_amplitude = attr.ib(default=1)
    pulse_samples = attr.ib(default=3600, validator=is_greater_equal(0))
    wait_samples_updated = attr.ib(default=0, validator=is_greater_equal(0))
    dead_samples_updated = attr.ib(default=0, validator=is_greater_equal(0))

    def write_sequence(self):
        # Call the method from parent class `Sequence` and then
        # overwrite it
        super().write_sequence()
        # Update the sequence type information in the header
        self.sequence = SequenceCommand.replace_sequence_type(
            self.sequence, SequenceType.PULSED_SPEC
        )
        self.sequence += SequenceCommand.inline_comment("Waveform definitions")
        # Define a square pulse of specified length
        self.sequence += SequenceCommand.init_ones(
            self.pulse_amplitude, self.pulse_samples
        )
        self.sequence += SequenceCommand.inline_comment("Trigger commands")
        # Wait for external trigger (depends on the trigger mode)
        self.sequence += self.trigger_cmd_wait
        # Compensate for trigger latency differences
        self.sequence += self.trigger_cmd_latency
        self.sequence += SequenceCommand.new_line()
        self.sequence += SequenceCommand.inline_comment("Start main sequence")
        # Start repeat loop in sequencer
        self.sequence += SequenceCommand.repeat(self.repetitions)
        # Play zeros to wait before playing the waveform (depends on
        # period, dead_time and alignment setting).
        self.sequence += SequenceCommand.tab() + SequenceCommand.play_zero(
            self.wait_samples_updated, self.target
        )
        # Reset oscillator phase
        self.sequence += SequenceCommand.tab() + self.osc_cmd_reset
        # Play the waveforms
        self.sequence += SequenceCommand.tab() + SequenceCommand.play_wave(
            target=self.target
        )
        # Trigger quantum analyzer
        self.sequence += SequenceCommand.tab() + self.readout_cmd_trigger
        # Play zeros to wait until end of period.
        self.sequence += SequenceCommand.tab() + SequenceCommand.play_zero(
            self.dead_samples_updated, self.target
        )
        # Finish repeat loop
        self.sequence += SequenceCommand.close_bracket()

    def update_params(self):
        # Phase of the modulation oscillator must be reset to 0 in this
        # sequence type, overwriting user preference
        self.reset_phase = True
        # Call the parent function to update all parameters including
        # the ones that depend on the `reset_phase` option. Note that
        # the parent class should not change `reset_phase` setting.
        super().update_params()
        # Convert pulse length to number of samples. Use floor division
        # operator `//` and round down to greatest multiple of 8.
        self.pulse_samples = self.time_to_samples(self.pulse_length) // 8 * 8
        # Update the number of samples to wait before and after playing
        # the pulse according to the alignment and pulse length.
        if self.alignment == Alignment.END_WITH_TRIGGER:
            self.wait_samples_updated = self.wait_samples - self.pulse_samples
            self.dead_samples_updated = self.dead_samples
        elif self.alignment == Alignment.START_WITH_TRIGGER:
            self.wait_samples_updated = self.wait_samples
            self.dead_samples_updated = self.dead_samples - self.pulse_samples

    def check_attributes(self):
        super().check_attributes()
        if self.alignment == Alignment.END_WITH_TRIGGER:
            if (
                self.period - self.dead_time + self.trigger_delay - self.pulse_length
            ) < 0:
                _logger.error(
                    "Wait time cannot be shorter than pulse length!",
                    _logger.ExceptionTypes.ValueError,
                )
        elif self.alignment == Alignment.START_WITH_TRIGGER:
            if (self.dead_time - self.trigger_delay - self.pulse_length) < 0:
                _logger.error(
                    "Dead time cannot be shorter than pulse length!",
                    _logger.ExceptionTypes.ValueError,
                )


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
        elif self.trigger_mode in [
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
        ]:
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
        >>>    ct_path="Path\to\valid\ct.json
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
    ct_path = attr.ib(default="")

    def write_sequence(self):
        self.sequence = SequenceCommand.header_comment(sequence_type="Custom")
        self.sequence += f"// from file: {self.path}\n\n"
        self.sequence += self.program

    def update_params(self):
        super().update_params()
        if self.path:
            self.program = Path(self.path).read_text()
        for i, p in enumerate(self.custom_params):
            self.program = self.program.replace(f"$param{i+1}$", str(p))

    def check_attributes(self):
        if self.path:
            p = Path(self.path)
            if p.suffix != ".seqc":
                _logger.error(
                    "Specified file is not a .seqc file!",
                    _logger.ExceptionTypes.ValueError,
                )

    def write_ct(self):
        """copy commandtable path"""
        if self.ct_path:
            self.ct = Path(self.ct_path).read_text()