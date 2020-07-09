# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time
from typing import List, Union

from zhinst.toolkit.helpers import SequenceProgram, Waveform, SequenceType
from .base import ToolkitError, BaseInstrument


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

    def _setup(self):
        self._module = self._parent._controller._connection.awg_module

    @property
    def index(self):
        return self._index

    @property
    def name(self):
        return self._parent.name + "-" + str(self._index)

    @property
    def waveforms(self):
        return self._waveforms

    @property
    def is_running(self):
        return self._parent._get(f"/awgs/{self._index}/enable")

    @property
    def sequence_params(self):
        return self._program.list_params()

    def __repr__(self):
        params = self.sequence_params["sequence_parameters"]
        s = f"{self._parent.name}: {super().__repr__()}\n"
        s += f"    parent  : {self._parent}\n"
        s += f"    index   : {self._index}\n"
        s += f"    sequence: \n"
        s += f"           type: {self.sequence_params['sequence_type']}\n"
        for i in params.items():
            s += f"            {i}\n"
        return s

    def run(self) -> None:
        """Runs the AWG Core."""
        self._parent._set(f"/awgs/{self._index}/enable", 1)

    def stop(self) -> None:
        """Stops the AWG Core."""
        self._parent._set(f"/awgs/{self._index}/enable", 0)

    def wait_done(self, timeout: float = 10) -> None:
        """Waits until the AWG Core is finished.
        
        Keyword Arguments:
            timeout (int): The maximum waiting time in seconds for the AWG Core. 
                (default: 10)

        """
        tok = time.time()
        while self.is_running:
            tik = time.time()
            time.sleep(0.1)
            if tik - tok > timeout:
                break

    def compile(self) -> None:
        """Compiles the current SequenceProgram on the AWG Core.
        
        Raises:
            ToolkitError: If the AWG Core has not been set up yet.
            ToolkitError: If the compilation has failed.
            Warning: If the compilation has finished with a warning.

        """
        if self._module is None:
            raise ToolkitError("This AWG is not connected to a awgModule!")
        self._module.update(device=self._parent.serial)
        self._module.update(index=self._index)
        if self._program.sequence_type == SequenceType.SIMPLE:
            buffer_lengths = [w.buffer_length for w in self._waveforms]
            delays = [w.delay for w in self._waveforms]
            self.set_sequence_params(buffer_lengths=buffer_lengths, delay_times=delays)
        self._module.set("compiler/sourcestring", self._program.get_seqc())
        while self._module.get_int("compiler/status") == -1:
            time.sleep(0.1)
        if self._module.get_int("compiler/status") == 1:
            raise ToolkitError(
                "Upload failed: \n" + self._module.get_string("compiler/statusstring")
            )
        if self._module.get_int("compiler/status") == 2:
            raise Warning(
                "Compiled with warning: \n"
                + self._module.get_string("compiler/statusstring")
            )
        if self._module.get_int("compiler/status") == 0:
            print("Compilation successful")
        tik = time.time()
        while (self._module.get_double("progress") < 1.0) and (self._module.get_int("/elf/status") != 1):
            time.sleep(0.1)
            if time.time() - tik >= 100: # 100s timeout
                raise ToolkitError("Program upload timed out!")
        status = self._module.get_int("/elf/status")
        print(
            f"{self.name}: Sequencer status: {'ELF file uploaded' if status == 0 else 'FAILED!!'}"
        )

    def reset_queue(self) -> None:
        """Resets the waveform queue to an empty list."""
        self._waveforms = []

    def queue_waveform(
        self,
        wave1: Union[List, np.array],
        wave2: Union[List, np.array],
        delay: float = 0,
    ) -> None:
        """Adds a new waveform to the queue. 
        
        Arguments:
            wave1 (array): The waveform to be queued for Channel 1 as a 1D numpy 
                array. 
            wave2 (array): The waveform to be queued for Channel 2 as a 1D numpy 
                array. 
        
        Keyword Arguments:
            delay (int): An individual delay in seconds for this waveform w.r.t. 
                the time origin of the sequence. (default: 0)
        
        Raises:
            Exception: If the sequence is not of type *'Simple'*.

        """
        if self._program.sequence_type != SequenceType.SIMPLE:
            raise Exception(
                "Waveform upload only possible for 'Simple' sequence program!"
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
        """Replaces a waveform in the queue at a given index.
        
        Arguments:
            wave1 (array): Waveform to replace current wave for Channel 1.
            wave2 (array): Waveform to replace current wave for Channel 2.
        
        Keyword Arguments:
            i (int): The index of the waveform in the queue to be replaced.
            delay (int): An individual delay in seconds for this waveform w.r.t. 
                the time origin of the sequence. (default: 0)
        
        Raises:
            ToolkitError: If the given index is out of range.

        """
        if i not in range(len(self._waveforms)):
            raise ToolkitError("Index out of range!")
        self._waveforms[i].replace_data(wave1, wave2, delay=delay)

    def upload_waveforms(self) -> None:
        """Uploads all waveforms in the queue to the AWG Core.

        This method only works as expected if the Sequence Program is in 
        *'Simple'* mode and has been compiled beforehand. See 
        :func:`compile_and_upload_waveforms(...)`.
        
        """
        waveform_data = [w.data for w in self._waveforms]
        nodes = [
            f"awgs/{self._index}/waveform/waves/{i}" for i in range(len(waveform_data))
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
        """Sets the parameters of the Sequence Program.

        Passes all the keyword arguments to the `set_param(...)` method of the 
        Sequence Program. The available sequence parameters may vary between 
        different sequences. For a list of all current sequence parameters see 
        the property `sequence_params`. 

        They include *'sequence_type'*, *'period'*, *'repetitions'*, 
        *'trigger_mode'*, *'trigger_delay'*, ...

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

    def _apply_sequence_settings(self, **kwargs):
        pass
