# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time
from typing import List, Union
import re
import logging
import traceback

from zhinst.toolkit.helpers import SequenceProgram, SHFWaveform, SequenceType
from .base import ToolkitError
from .shf_channel import SHFChannel

logging.basicConfig(format="%(levelname)s: %(message)s")
_logger = logging.getLogger(__name__)


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
    """

    def __init__(self, parent: SHFChannel) -> None:
        self._parent = parent
        self._index = self._parent._index
        self._device = self._parent._parent
        self._module = None
        self._waveforms = []
        self._program = SequenceProgram()
        self.set_sequence_params(target=self._device.device_type)

    def _setup(self):
        self._module = self._device._controller._connection.awg_module

    def _init_generator_params(self):
        """Initialize parameters associated with device generators.

        Can be overwritten by any Generator that inherits from the
        :class:`SHFGenerator`.

        """
        pass

    @property
    def name(self):
        return self._device.name + "-" + "generator" + "-" + str(self._index)

    @property
    def waveforms(self):
        return self._waveforms

    @property
    def is_running(self):
        return self.enable

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

    def run(self) -> None:
        """Run the generator."""
        self.enable(1)

    def stop(self) -> None:
        """Stops the generator."""
        self.enable(0)

    def wait_done(self, timeout: float = 10) -> None:
        """Waits until the Generator is finished.

        Keyword Arguments:
            timeout (int): The maximum waiting time in seconds for the
                Generator (default: 10).

        """
        tok = time.time()
        while self.is_running:
            tik = time.time()
            time.sleep(0.1)
            if tik - tok > timeout:
                break

    def compile(self) -> None:
        """Compile the current SequenceProgram and load it to sequencer.

        Raises:
            ToolkitError: If the AWG Core has not been set up yet.
            ToolkitError: If the compilation has failed.
            Warning: If the compilation has finished with a warning.
        """
        if self._module is None:
            raise ToolkitError("This Generator is not connected to an awgModule!")
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
                f"{self._caller_name()}\n"
                f"Please check the sequencer code for {self.name}:\n{self._seqc_error(statusstring)}"
                f"Compiler status string:\n{statusstring}\n",
            )
            raise ToolkitError("Compilation failed")
        elif compiler_status == 2:
            _logger.warning(
                f"{self._caller_name()}\n"
                f"Please check the sequencer code for {self.name}:\n{self._seqc_error(statusstring)}"
                f"Compiler status string:\n{statusstring}\n",
            )
        elif compiler_status == 0:
            _logger.info(f"{self.name}: Compilation successful")
        tik = time.time()
        while (self._module.get_double("progress") < 1.0) and (
            self._module.get_int("/elf/status") != 1 and self.ready != 1
        ):
            time.sleep(0.1)
            if time.time() - tik >= 100:  # 100s timeout
                raise ToolkitError(f"{self.name}: Program upload timed out!")
        elf_status = self._module.get_int("/elf/status")
        if elf_status == 0:
            _logger.info(f"{self.name}: Sequencer status: ELF file uploaded!")
        else:
            _logger.error(
                f"{self._caller_name()}\n"
                f"{self.name}: Sequencer status: ELF upload failed!",
            )
            raise ToolkitError(f"{self.name}: ELF upload failed!")

    def reset_queue(self) -> None:
        """Resets the waveform queue to an empty list."""
        self._waveforms = []

    def queue_waveform(self, wave: Union[List, np.array], delay: float = 0) -> None:
        """Add a new waveform to the queue.

        Arguments:
            wave (array): The waveform to be queued as a 1D numpy array.

        Keyword Arguments:
            delay (int): An individual delay in seconds for this waveform
                w.r.t. the time origin of the sequence. (default: 0)

        Raises:
            Exception: If the sequence is not of type *'Custom'*.
        """
        if self._program.sequence_type != SequenceType.CUSTOM:
            raise Exception(
                "Waveform upload only possible for 'Custom' sequence program!"
            )
        self._waveforms.append(SHFWaveform(wave, delay=delay))
        print(f"Current length of queue: {len(self._waveforms)}")

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
        self._device._setVector(zip(nodes, waveform_data))
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

            >>> shfqa.channels[0].generator

            <zhinst.toolkit.control.drivers.shfqa.Generator object at 0x0000016B7B71DDC8>
                parent  : <zhinst.toolkit.control.drivers.shfqa.Channel object at 0x0000016B7B71D508>
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

            >>> shfqa.channels[0].generator.set_sequence_params(
            >>>     sequence_type="Custom",
            >>>     program = seqc_program_string,
            >>>     custom_params = [param1, param2],
            >>> )

        """
        self._program.set_params(**kwargs)
        self._apply_sequence_settings(**kwargs)

    def _apply_sequence_settings(self, **kwargs):
        pass

    def _seqc_error(self, statusstring):
        """Extract the relevant lines from seqc program in case of error.

        Ihis method extracts the line number from the compiler status
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

    def _caller_name(self):
        """Return the caller name.

        This method returns the line that calls a function. It is used
        to display a logging message to the user and show which line
        caused an error or warning.
        """
        frame_list = traceback.StackSummary.extract(traceback.walk_stack(None))
        for frame in frame_list:
            if frame.name == "<module>":
                return frame.line
