# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time
from typing import List, Union
import re

from zhinst.toolkit.helpers import (
    SequenceProgram,
    SHFWaveform,
    SequenceType,
    TriggerMode,
)
from zhinst.toolkit.interface import LoggerModule
from .shf_qachannel import SHFQAChannel

_logger = LoggerModule(__name__)


class SHFGenerator:
    """Implements an SHF Generator representation.

    The :class:`SHFGenerator` class implements basic functionality of
    the SHF Sequencer allowing the user to write and upload their
    *'.seqC'* code.

    In contrast to other AWG Sequencers, e.g. from the HDAWG, SHF
    Sequencer does not provide writing access to the Waveform Memories
    and hence does not come with predefined waveforms such as `gauss`
    or `ones`. Therefore, all waveforms need to be defined in Python
    and uploaded to the device using `upload_waveforms` method.

    For example, the generator can be programmed with a custom .seqc
    code like this:

        >>> generator = shf.qachannels[0].generator
        >>> ...
        >>> wait_time = 512
        >>> custom_program='''
        >>> waitDigTrigger(1);
        >>> wait($param1$);
        >>> startQA(QA_GEN_0, QA_INT_0, true,  0, 0x1 );
        >>> wait($param1$);
        >>> startQA(QA_GEN_1, QA_INT_1, true,  0, 0x0 );
        >>> wait($param1$);
        >>> startQA(QA_GEN_2, QA_INT_2, true,  0, 0x0 );
        >>> '''
        >>> generator.set_sequence_params(
        >>>     sequence_type="Custom",
        >>>     program = custom_program,
        >>>     custom_params = [wait_time],
        >>> )

    The user can also upload waveforms defined as numpy arrays:

        >>> wave = np.linspace(1, 0, wave_length)
        >>> amps = np.linspace(0.5, 1, 3)
        >>> data = [amp * wave for amp in amps]
        >>> generator.reset_queue()
        >>> for wave in data:
        >>>     generator.queue_waveform(wave)
        Current length of queue: 1
        Current length of queue: 2
        Current length of queue: 3
        ...
        >>> generator.compile()
        >>> generator.upload_waveforms()
        Upload of 3 waveforms took 0.20744 s

    To run the sequencer and play the uploaded waveforms:

        >>> generator.run()
        >>> generator.wait_done()

    Attributes:
        parent (:class:`SHFQAChannel`): The parent qachannel that this
            :class:`SHFGenerator` is associated to.
        device (:class:`BaseInstrument`): The instrument that this
            :class:`SHFGenerator` is associated to.
        index (int): An integer specifying the index in the instrument.
        waveforms (list): A list of :class:`SHFWaveform` s that
            represent the queued up waveforms in for a *'Custom'*
            sequence.
        name (str): The name of the `SHFGenerator`.
        is_running (bool): A flag that shows if the `SHFGenerator` is
            currently running or not.
        sequence_params (dict): A dictionary of all the sequence
            parameters currently set on the `SequenceProgram`.

    """

    def __init__(self, parent: SHFQAChannel) -> None:
        self._parent = parent
        self._index = self._parent._index
        self._device = self._parent._parent
        self._module = None
        self._waveforms = []
        self._program = SequenceProgram()
        self.set_sequence_params(target=self._device.device_type)

    def _setup(self):
        self._module = self._device._controller.connection.awg_module

    def _init_generator_params(self):
        """Initialize parameters associated with device generators.

        Can be overwritten by any Generator that inherits from the
        :class:`SHFGenerator`.

        """
        pass

    @property
    def parent(self):
        return self._parent

    @property
    def device(self):
        return self._device

    @property
    def index(self):
        return self._index

    @property
    def name(self):
        return self._device.name + "-" + "generator" + "-" + str(self._index)

    @property
    def waveforms(self):
        return self._waveforms

    @property
    def is_running(self):
        return self._enable()

    @property
    def sequence_params(self):
        return self._program.list_params()

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

    def run(self, sync=True) -> None:
        """Run the generator.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after enabling the generator (default: True).

        """
        self._enable(True, sync=sync)

    def stop(self, sync=True) -> None:
        """Stop the generator.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after disabling the generator (default: True).

        """
        self._enable(False, sync=sync)

    def wait_done(self, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the generator is finished.

        Arguments:
            timeout (float): The maximum waiting time in seconds for the
                generator (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting generator state

        Raises:
            ToolkitError: If the generator is running in continuous
                mode.
            TimeoutError: If the generator is not finished before the
                timeout.

        """
        if not self.single():
            _logger.error(
                "The generator is running in continuous mode, it will never be "
                "finished.",
                _logger.ExceptionTypes.ToolkitError,
            )
        start_time = time.time()
        while self.is_running and start_time + timeout >= time.time():
            time.sleep(sleep_time)
        if self.is_running and start_time + timeout < time.time():
            _logger.error(
                "Generator timed out!",
                _logger.ExceptionTypes.TimeoutError,
            )

    def compile(self) -> None:
        """Compile the current SequenceProgram and load it to sequencer.

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
                "This Generator is not connected to an awgModule!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        self._module.update(device=self._device.serial)
        self._module.update(index=self._index)
        seqc_program = self._program.get_seqc()
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
            self._module.get_int("/elf/status") != 1 and self._ready != 1
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

    def reset_queue(self) -> None:
        """Resets the waveform queue to an empty list."""
        self._waveforms = []

    def queue_waveform(self, wave: Union[List, np.array], delay: float = 0) -> None:
        """Add a new waveform to the queue.

        Arguments:
            wave (array): The waveform to be queued as a 1D numpy array.
            delay (int): An individual delay in seconds for this waveform
                w.r.t. the time origin of the sequence. (default: 0)

        Raises:
            ToolkitError: If the sequence is not of type *'Custom'*.

        """
        if self._program.sequence_type != SequenceType.CUSTOM:
            _logger.error(
                "Waveform upload only possible for 'Custom' sequence program!",
                _logger.ExceptionTypes.ToolkitError,
            )
        self._waveforms.append(SHFWaveform(wave, delay=delay))
        print(f"Current length of queue: {len(self._waveforms)}")

    def replace_waveform(
        self,
        wave: Union[List, np.array],
        i: int = 0,
        delay: float = 0,
    ) -> None:
        """Replace a waveform in the queue at a given index.

        Arguments:
            wave (array): Waveform to replace current wave
            i (int): The index of the waveform in the queue to be
                replaced.
            delay (int): An individual delay in seconds for this
                waveform w.r.t. the time origin of the sequence. (default: 0)

        Raises:
            ValueError: If the given index is out of range.

        """
        if i not in range(len(self._waveforms)):
            _logger.error(
                "Index out of range!",
                _logger.ExceptionTypes.ValueError,
            )
        self._waveforms[i].replace_data(wave, delay=delay)

    def upload_waveforms(self) -> None:
        """Upload all waveforms in the queue to the Generator.

        This method only works as expected if the Sequence Program has
        been compiled beforehand.
        See :func:`compile_and_upload_waveforms(...)`.
        """
        waveform_data = [w.data for w in self._waveforms]
        nodes = [
            f"qachannels/{self._index}/generator/waveforms/{i}/wave"
            for i in range(len(waveform_data))
        ]
        tok = time.time()
        self._device._set_vector(zip(nodes, waveform_data))
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
        """Sets the parameters of the Sequence Program.

        Passes all the keyword arguments to the `set_param(...)` method
        of the Sequence Program. The available sequence parameters may
        vary between different sequences. For a list of all current
        sequence parameters see the property `sequence_params`.

        They include *'sequence_type'*, *'period'*, *'repetitions'*,
        *'trigger_mode'*, *'trigger_delay'*, ...

            >>> shfqa.qachannels[0].generator
            <zhinst.toolkit.control.drivers.shfqa.Generator object at 0x0000016B7B71DDC8>
                parent  : <zhinst.toolkit.control.drivers.shfqa.QAChannel object at 0x0000016B7B71D508>
                index   : 0
                sequence:
                    type: SequenceType.CUSTOM
                    ('target', <DeviceTypes.SHFQA: 'shfqa'>)
                    ('clock_rate', 2400000000.0)
                    ('period', 0.0001)
                    ('trigger_mode', <TriggerMode.SEND_TRIGGER: 'Send Trigger'>)
                    ('trigger_samples', 32)
                    ('repetitions', 1)
                    ('alignment', <Alignment.END_WITH_TRIGGER: 'End with Trigger'>)
                    ...

            >>> shfqa.qachannels[0].generator.set_sequence_params(
            >>>     sequence_type="Custom",
            >>>     program = seqc_program_string,
            >>>     custom_params = [param1, param2],
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
            if t not in self._device.allowed_sequences:
                _logger.error(
                    f"Sequence type {t} must be one of "
                    f"{[s.value for s in self._device.allowed_sequences]}!",
                    _logger.ExceptionTypes.ToolkitError,
                )
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "None":
                # If trigger mode is given as string `None`, return
                # enumeration for `None` from the TriggerMode class
                t = TriggerMode(None)
            else:
                t = TriggerMode(kwargs["trigger_mode"])
            if t not in self._device.allowed_trigger_modes:
                _logger.error(
                    f"Trigger mode {t} must be one of "
                    f"{[s.value for s in self._device.allowed_trigger_modes]}!",
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
