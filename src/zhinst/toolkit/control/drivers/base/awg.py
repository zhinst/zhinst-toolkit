# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time
from typing import List, Union
import re
from zhinst.toolkit.control.drivers.base.ct import CommandTable

from zhinst.toolkit.helpers import SequenceProgram, Waveform, SequenceType, TriggerMode
from zhinst.toolkit.interface.interface import DeviceTypes
from .base import BaseInstrument
from zhinst.toolkit.interface import LoggerModule
from ...parsers import Parse

_logger = LoggerModule(__name__)


class AWGCore:
    """Implements an AWG Core representation.

    The :class:`AWGCore` class implements basic functionality of the AWG
    sequencer without the need for the user to write their own *'.seqC'* code.
    The :class:`AWGCore` holds a :class:`SequenceProgram` object whose
    parameters can be set using the `set_sequence_params(...)` method of the
    AWG.

    This module takes over the functionality of configuring the seuqence program
    and compiling it on the instrument. Given the 'Simple' sequence type,
    sample-defined waveforms can be queued and uploaded to the AWG.

    This base class :class:`AWGCore` is inherited by device-specific AWGs for
    the HDAWG or the UHFQA/UHFLI. The device-specific AWGs add certain
    `zhinst-toolkit` :class:`Parameters` and apply certain
    instrument settings, depending on the `sequence_type` and the `trigger_mode`
    (sending out a trigger signal or waiting for a trigger) of the sequence
    program.

    For example, a predefined Rabi sequence with a sweep over 101 different
    amplitudes could be programmed like this:

        >>> awg = hdawg.awgs[0]
        >>> awg.set_sequence_params(
        >>>     sequence_type="Rabi",
        >>>     trigger_mode="None",
        >>>     repetitions=1e3,
        >>>     period=20e-6,
        >>>     pulse_amplitudes=np.linspace(0, 1.0, 101),
        >>>     pulse_width=20e-9,
        >>>     pulse_truncation=4,
        >>> )
        >>> awg.compile()
        >>> ...
        >>> awg.run()
        >>> awg.wait_done()

    The sequence type *'Simple'* allows the user to upload sample-defined
    waveforms as numpy arrays. The waveforms in the queue are played one after
    the other with a specified period and alignment/delay to a time origin.

        >>> awg.set_sequence_params(
        >>>     sequence_type="Simple",
        >>>     trigger_mode="Send Trigger",
        >>>     repetitions=1e3,
        >>>     period=20e-6,
        >>> )
        >>> for amp in np.linspace(-1, 1, 101):
        >>>     wave = amp * np.linspace(-1.0, 1.0, 800)
        >>>     awg.queue_waveform(wave, -wave)
        Current length of queue: 1
        Current length of queue: 2
        Current length of queue: 3
        Current length of queue: 4
        ...
        >>> awg.compile_and_upload_waveforms()
        Compilation successful
        hd1-0: Sequencer status: ELF file uploaded
        Upload of 101 waveforms took 0.20005226135253906 s
        >>> awg.run()
        >>> awg.wait_done()

    Attributes:
        parent (:class:`BaseInstrument`): The parent instrument that this
            :class:`AWGCore` is associated to.
        index (int): An integer specifying the index in the parent instrument.
        waveforms (list): A list of :class:`Waveforms` that represent the
            queued up waveforms in for a *'Simple'* sequence.
        program (:class:`SequenceProgram`): A :class:`SequenceProgram` object
            used to program predefined *'.seqC'* sequences on the device.
        name (str): The name of the `AWG Core`.
        is_running (bool): A flag that shows if the `AWG Core` is currently
            running or not.
        sequence_params (dict): A dictionary of all the sequence parameters
            currently set on the `SequenceProgram`.

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        self._parent = parent
        self._index = index
        self._module = None
        self._waveforms = []
        self._program = SequenceProgram()
        self.set_sequence_params(target=self._parent.device_type)
        self._ct = None

    def _setup(self):
        self._module = self._parent._controller.connection.awg_module

    def _init_awg_params(self):
        """Initialize parameters associated with device AWG nodes.

        Can be overwritten by any AWG core that inherits from the
        :class:`AWGCore`.

        """
        pass

    def _init_ct(self, ct_schema_url, ct_node):
        self._ct = CommandTable(self, ct_schema_url, ct_node)

    @property
    def index(self):
        return self._index

    @property
    def name(self):
        return self._parent.name + "-" + "awg" + "-" + str(self._index)

    @property
    def waveforms(self):
        return self._waveforms

    @property
    def is_running(self):
        return self._enable()

    @property
    def sequence_params(self):
        return self._program.list_params()

    @property
    def ct(self):
        return self._ct

    def __repr__(self):
        params = self.sequence_params["sequence_parameters"]
        s = f"{super().__repr__()}\n"
        s += f"    parent  : {self._parent}\n"
        s += f"    index   : {self._index}\n"
        s += f"    sequence: \n"
        s += f"            type: {self.sequence_params['sequence_type']}\n"
        for i in params.items():
            s += f"            {i}\n"
        return s

    def outputs(self, value=None):
        """Sets both signal outputs simultaneously.

        Arguments:
            value (tuple): Tuple of values {'on', 'off'} for channel 1
                and 2 (default: None).

        Returns:
            A tuple with the states {'on', 'off'} for the two output
            channels if the keyword argument is not given.

        Raises:
            ValueError: If the `value` argument is not a list or tuple
                of length 2.

        """
        if self._parent.device_type == DeviceTypes.SHFSG:
            if value is None:
                output_states = (self.output1(), self.output2())
                return Parse.get_on_off_tuple_list(self.output_states(), 2)
            else:
                _logger.error(
                    "The AWG outputs of the SHFSG are read only. Please use the output control of the \
                    SG Channel to enable or disable the physical output of the instrument.",
                    _logger.ExceptionTypes.ToolkitError,
                )
        else:
            if value is None:
                output_states = (self.output1(), self.output2())
                return Parse.get_on_off_tuple_list(output_states, 2)
            else:
                output_states = Parse.set_on_off_tuple_list(value, 2)
                self.output1(output_states[0])
                self.output2(output_states[1])

    def run(self, sync=True) -> None:
        """Run the AWG Core.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after enabling the AWG Core (default: True).

        """
        self._enable(True, sync=sync)

    def stop(self, sync=True) -> None:
        """Stop the AWG Core.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after disabling the AWG Core (default: True).

        """
        self._enable(False, sync=sync)

    def wait_done(self, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the AWG Core is finished.

        Arguments:
            timeout (float): The maximum waiting time in seconds for the
                AWG Core (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting AWG state

        Raises:
            ToolkitError: If the AWG is running in continuous mode.
            TimeoutError: If the AWG is not finished before the timeout.

        """
        if not self.single():
            _logger.error(
                "The AWG is running in continuous mode, it will never be finished.",
                _logger.ExceptionTypes.ToolkitError,
            )
        start_time = time.time()
        while self.is_running and start_time + timeout >= time.time():
            time.sleep(sleep_time)
        if self.is_running and start_time + timeout < time.time():
            _logger.error(
                "AWG Core timed out!",
                _logger.ExceptionTypes.TimeoutError,
            )

    def compile(self) -> None:
        """Compiles the current SequenceProgram on the AWG Core.

        Raises:
            ToolkitConnectionError: If the AWG Core has not been set up
                yet
            ToolkitError: if the compilation has failed or the ELF
                upload is not successful.
            TimeoutError: if the program upload is not completed before
                timeout.

        """
        if self._module is None:
            _logger.error(
                "This AWG is not connected to an awgModule!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        self._module.update(device=self._parent.serial)
        self._module.update(index=self._index)
        if self._program.sequence_type == SequenceType.SIMPLE:
            buffer_lengths = [w.buffer_length for w in self._waveforms]
            delays = [w.delay for w in self._waveforms]
            self.set_sequence_params(buffer_lengths=buffer_lengths, delay_times=delays)
        seqc_program, ct = self._program.get_seqc_ct()
        self._module.set("compiler/sourcestring", seqc_program)
        compiler_status = self._module.get_int("compiler/status")
        while compiler_status == -1:
            time.sleep(0.1)
            compiler_status = self._module.get_int("compiler/status")
        statusstring = self._module.get_string("compiler/statusstring")
        if compiler_status == 1:
            _logger.error(
                f"Please check the sequencer code for {self.name}:\n"
                f"{self._seqc_error(statusstring)}"
                f"Compiler status string:\n{statusstring}\n",
                _logger.ExceptionTypes.ToolkitError,
            )
        elif compiler_status == 2:
            _logger.warning(
                f"Please check the sequencer code for {self.name}:\n"
                f"{self._seqc_error(statusstring)}"
                f"Compiler status string:\n{statusstring}\n",
            )
        elif compiler_status == 0:
            _logger.info(f"{self.name}: Compilation successful")
        tik = time.time()
        while (self._module.get_double("progress") < 1.0) and (
            self._module.get_int("/elf/status") != 1
        ):
            time.sleep(0.1)
            if time.time() - tik >= 100:  # 100s timeout
                _logger.error(
                    f"{self.name}: Program upload timed out!",
                    _logger.ExceptionTypes.TimeoutError,
                )
        elf_status = self._module.get_int("/elf/status")
        if elf_status == 0:
            _logger.info(f"{self.name}: Sequencer status: ELF file uploaded!")
        else:
            _logger.error(
                f"{self.name}: Sequencer status: ELF upload failed!",
                _logger.ExceptionTypes.ToolkitError,
            )
        if ct:
            self._ct.load(ct)

    def reset_queue(self) -> None:
        """Resets the waveform queue to an empty list."""
        self._waveforms = []

    def queue_waveform(
        self,
        wave1: Union[List, np.array],
        wave2: Union[List, np.array],
        delay: float = 0,
    ) -> None:
        """Queues up a waveform to the *AWG Core*.

        Uploading custom waveforms is only possible when using the
        *'Simple'* or *'Custom'* sequence types. The waveform is
        specified with two numpy arrays for the two channels of the
        *AWG Core*. The waveform will then automatically align them to
        the correct minimum waveform length, sample granularity and
        scaling. An individual delay can be specified to shift the
        individual waveform with respect to the time origin of the
        period.

        Arguments:
            wave1 (array like): A list or array of samples in the
                waveform to be queued for channel 1. An empty list '[]'
                will upload zeros of the minimum waveform length.
            wave2 (array like): A list or array of samples in the
                waveform to be queued for channel 2. An empty list '[]'
                will upload zeros of the minimum waveform length.
            delay (float): An individual delay for the queued sequence
                with respect to the time origin. Positive values shift
                the start of the waveform forwards in time. (default: 0)

        Raises:
            ToolkitError: If the sequence is not of type *'Simple'* or
                *'Custom'*.

        """
        if self._program.sequence_type not in [
            SequenceType.SIMPLE,
            SequenceType.CUSTOM,
        ]:
            _logger.error(
                "Waveform upload only possible for 'Simple' and 'Custom' sequence "
                "programs!",
                _logger.ExceptionTypes.ToolkitError,
            )
        self._waveforms.append(Waveform(wave1, wave2, delay=delay))
        print(f"Current length of queue: {len(self._waveforms)}")

    def replace_waveform(
        self,
        wave1: Union[List, np.array],
        wave2: Union[List, np.array],
        i: int = 0,
        delay: float = 0,
    ) -> None:
        """Replaces the data in a waveform in the queue.

        The new data must have the same length as the previous data
        s.t. the waveform data can be replaced without recompilation of
        the sequence program.

        Arguments:
            wave1 (array): Waveform to replace current wave for
                Channel 1.
            wave2 (array): Waveform to replace current wave for
                Channel 2.
            i (int): The index of the waveform in the queue to be
                replaced.
            delay (int): An individual delay in seconds for this
                waveform w.r.t. the time origin of the sequence
                (default: 0).

        Raises:
            ValueError: If the given index is out of range.

        """
        if i not in range(len(self._waveforms)):
            _logger.error(
                "Index out of range!",
                _logger.ExceptionTypes.ValueError,
            )
        self._waveforms[i].replace_data(wave1, wave2, delay=delay)

    def upload_waveforms(self) -> None:
        """Uploads all waveforms in the queue to the AWG Core.

        This method only works as expected if the Sequence Program is in
        'Simple' or 'Custom' modes and has been compiled beforehand.
        See :func:`compile_and_upload_waveforms(...)`.
        """
        waveform_data = [w.data for w in self._waveforms]
        if self._parent.device_type == DeviceTypes.SHFSG:
            nodes = [
                f"sgchannels/{self._index}/awg/waveform/waves/{i}"
                for i in range(len(waveform_data))
            ]
        else:
            nodes = [
                f"awgs/{self._index}/waveform/waves/{i}"
                for i in range(len(waveform_data))
            ]
        tok = time.time()
        self._parent._set(zip(nodes, waveform_data))
        tik = time.time()
        print(f"Upload of {len(waveform_data)} waveforms took {tik - tok:.5} s")

    def compile_and_upload_waveforms(self) -> None:
        """Compiles the Sequence Program and uploads the queued waveforms.

        Simply combines the two methods to make sure the sequence is compiled
        before the waveform queue is uplaoded.
        """
        self.compile()
        self.upload_waveforms()

    def set_sequence_params(self, **kwargs) -> None:
        """Sets the parameters of the *Sequence Program*.

        Passes all the keyword arguments to the `set_param(...)` method of the
        *Sequence Program*. The available sequence parameters may vary between
        different sequences. For a list of all current sequence parameters see
        the method `sequence_params()`.

        They include:
            *'sequence_type', 'period', 'repetitions', 'trigger_mode',
            'trigger_delay', ...*

            >>> hdawg.awgs[0]
            <zhinst.toolkit.hdawg.AWG object at 0x0000021E467D3320>
                parent  : <zhinst.toolkit.hdawg.HDAWG object at 0x0000021E467D3198>
                index   : 0
                sequence:
                        type: None
                        ('target', 'hdawg')
                        ('clock_rate', 2400000000.0)
                        ('period', 0.0001)
                        ('trigger_mode', 'None')
                        ('repetitions', 1)
                        ('alignment', 'End with Trigger')
                        ...
            >>> hdawg.awgs[0].set_sequence_params(
            >>>     sequence_type="Simple",
            >>>     trigger_mode="Send Trigger",
            >>>     repetitions=1e6,
            >>>     alignemnt="Start with Trigger"
            >>> )

        """
        self._program.set_params(**kwargs)
        self._apply_sequence_settings(**kwargs)

    def _apply_sequence_settings(self, **kwargs) -> None:
        if "sequence_type" in kwargs.keys():
            if kwargs["sequence_type"] == "None":
                # If sequence type is given as string `None`, return
                # enumeration for `None` from the SequenceType class
                t = SequenceType(None)
            elif kwargs["sequence_type"] in ["Ramsey", "T2"] :
                t = SequenceType("T2*")
            else:
                t = SequenceType(kwargs["sequence_type"])
            if t not in self._parent.allowed_sequences:
                _logger.error(
                    f"Sequence type {t} must be one of "
                    f"{[s.value for s in self._parent.allowed_sequences]}!",
                    _logger.ExceptionTypes.ToolkitError,
                )
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "None":
                # If trigger mode is given as string `None`, return
                # enumeration for `None` from the TriggerMode class
                t = TriggerMode(None)
            else:
                t = TriggerMode(kwargs["trigger_mode"])
            if t not in self._parent.allowed_trigger_modes:
                _logger.error(
                    f"Trigger mode {t} must be one of "
                    f"{[s.value for s in self._parent.allowed_trigger_modes]}!",
                    _logger.ExceptionTypes.ToolkitError,
                )

    def _seqc_error(self, statusstring):
        """Extract the relevant lines from seqc program in case of error.

        This method extracts the line number from the compiler status
        and then finds the relevant lines in the seqc program to guide
        the user. It works both for errors and warnings.
        """
        seqc_error = "\n"
        seqc = self._program.get_seqc().splitlines()
        pattern = "line: (.*?)\):"
        num_error_line = int(re.search(pattern, statusstring).group(1))
        start_line = max(0, num_error_line - 4)
        stop_line = min(len(seqc), num_error_line + 1)
        number_width = len(str(stop_line + 1))
        for i, line in enumerate(seqc[start_line:stop_line], start=start_line):
            if i + 1 == num_error_line:
                seqc_error += f"-> {i + 1: >{number_width}}   {line.strip()}\n"
            else:
                seqc_error += f"   {i + 1: >{number_width}}   {line.strip()}\n"
        seqc_error += "\n"
        return seqc_error
