# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from zhinst.toolkit.helpers import SequenceProgram, Waveform
from .base import ZHTKException


class AWGCore:
    """
    Implements an AWG Core representation.

    Attributes:
        parent (BaseInstrument): reference to the parent instrument
        index (int): integer specifying the index in the parent instrument
        waveforms (list): list of waveforms that represent the queued up waves
        program (SequenceProgram): a sequence program object used to program 
            certain seqC sequences onto the device
    

    """

    def __init__(self, parent, index):
        self._parent = parent
        self._index = index
        self._waveforms = []
        self._program = SequenceProgram()
        self.set_sequence_params(target=self._parent.device_type)

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

    def run(self):
        self._parent._set(f"/awgs/{self._index}/enable", 1)
        # print(f"Started AWG {self.name}!")

    def stop(self):
        self._parent._set(f"/awgs/{self._index}/enable", 0)
        # print(f"Stopped AWG {self.name}!")

    def wait_done(self, timeout=10):
        tok = time.time()
        while self.is_running:
            tik = time.time()
            time.sleep(0.1)
            if tik - tok > timeout:
                break
        return

    def compile(self):
        awg_module = self._parent._awg_connection
        awg_module.update(device=self._parent.serial)
        awg_module.update(index=self._index)
        if self._program.sequence_type == "Simple":
            buffer_lengths = [w.buffer_length for w in self._waveforms]
            delays = [w.delay for w in self._waveforms]
            self.set_sequence_params(buffer_lengths=buffer_lengths, delay_times=delays)
        awg_module.set("compiler/sourcestring", self._program.get_seqc())
        while awg_module.get_int("compiler/status") == -1:
            time.sleep(0.1)
        if awg_module.get_int("compiler/status") == 1:
            raise Exception(
                "Upload failed: \n" + awg_module.get_string("compiler/statusstring")
            )
        if awg_module.get_int("compiler/status") == 2:
            raise Warning(
                "Compiled with warning: \n"
                + awg_module.get_string("compiler/statusstring")
            )
        if awg_module.get_int("compiler/status") == 0:
            print("Compilation successful")
        self._wait_upload_done()

    def reset_queue(self):
        self._waveforms = []

    def queue_waveform(self, wave1, wave2, delay=0):
        if self._program.sequence_type != "Simple":
            raise Exception(
                "Waveform upload only possible for 'Simple' sequence program!"
            )
        self._waveforms.append(Waveform(wave1, wave2, delay=delay))
        print(f"Current length of queue: {len(self._waveforms)}")

    def replace_waveform(self, wave1, wave2, i=0, delay=0):
        if i not in range(len(self._waveforms)):
            raise Exception("Index out of range!")
        self._waveforms[i].replace_data(wave1, wave2, delay=delay)

    def upload_waveforms(self):
        waveform_data = [w.data for w in self._waveforms]
        nodes = [
            f"awgs/{self._index}/waveform/waves/{i}" for i in range(len(waveform_data))
        ]
        tok = time.time()
        self._parent._set(zip(nodes, waveform_data))
        tik = time.time()
        print(f"Upload of {len(waveform_data)} waveforms took {tik - tok:.5} s")

    def compile_and_upload_waveforms(self):
        self.compile()
        self.upload_waveforms()

    def _wait_upload_done(self, timeout=10):
        time.sleep(0.01)
        awg_module = self._parent._awg_connection
        awg_module.update(device=self._parent.serial, index=self._index)
        tik = time.time()
        while awg_module.get_int("/elf/status") == 2:
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise Exception("Program upload timed out!")
        status = awg_module.get_int("/elf/status")
        print(
            f"{self.name}: Sequencer status: {'ELF file uploaded' if status == 0 else 'FAILED!!'}"
        )

    def set_sequence_params(self, **kwargs):
        self._program.set_params(**kwargs)
        self._apply_sequence_settings(**kwargs)

    def _apply_sequence_settings(self, **kwargs):
        pass
