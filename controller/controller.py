import json
import time

from .baseController import BaseController
from helpers import SequenceProgram, Waveform, Compiler


class Controller(BaseController):
    def __init__(self):
        super().__init__()
        self._compiler = None

    def connect_device(self, name):
        super().connect_device(name)
        dev = self._instrument_config.instruments[0].setup[0]  # only one device for now
        self._compiler = Compiler(dev)

    def awg_compile(self, awg):
        self._connection.awgModule.update(index=awg, device=self._device.serial)
        if self._compiler.sequence_type(awg) == "Simple":
            buffer_lengths = [w.buffer_length for w in self._device.awgs[awg].waveforms]
            self._compiler.set_parameter(awg, buffer_lengths=buffer_lengths)
        self.__update_awg_program(awg)
        program = self._device.awgs[awg].get_program()
        self._connection.awgModule.set("compiler/sourcestring", program)
        while self._connection.awgModule.get_int("compiler/status") == -1:
            time.sleep(0.1)
        if self._connection.awgModule.get_int("compiler/status") == 1:
            raise Exception(
                "Upload failed: \n"
                + self._connection.awgModule.get_string("compiler/statusstring")
            )
        if self._connection.awgModule.get_int("compiler/status") == 2:
            raise Warning(
                "Compiled with warning: \n"
                + self._connection.awgModule.get_string("compiler/statusstring")
            )
        if self._connection.awgModule.get_int("compiler/status") == 2:
            print("Compilation successful")
        self.__wait_upload_done(awg)

    def awg_run(self, awg):
        self.set(f"/awgs/{awg}/enable", 1)
        print(f"Started AWG {awg}!")

    def awg_stop(self, awg):
        self.set(f"/awgs/{awg}/enable", 0)
        print(f"Stopped AWG {awg}!")

    def awg_is_running(self, awg):
        return bool(self._connection.awgModule.get_int("awg/enable", index=awg))

    def awg_queue_waveform(self, awg, waveform: Waveform, **kwargs):
        if self._compiler.sequence_type(awg) != "Simple":
            raise Exception("Waveform upload only possible for 'Simple' sequence!")
        self._device.awgs[awg].waveforms.append(waveform)
        print(f"current length of queue: {len(self._device.awgs[awg].waveforms)}")

    def awg_upload_waveforms(self, awg):
        waveform_data = [w.data for w in self._device.awgs[awg].waveforms]
        self.awg_compile(awg)
        nodes = [f"awgs/{awg}/waveform/waves/{i}" for i in range(len(waveform_data))]
        self.set(zip(nodes, waveform_data))
        self._device.awgs[awg].reset_waveforms()

    def awg_set_sequence_params(self, awg, **kwargs):
        self._compiler.set_parameter(awg, **kwargs)
        self.__update_awg_program(awg)

    def awg_list_params(self, awg):
        return self._compiler.list_params(awg)

    def __update_awg_program(self, awg):
        program = self._compiler.get_program(awg)
        self._device.awgs[awg].set_program(program)

    def __wait_upload_done(self, awg, timeout=10):
        time.sleep(0.01)
        node = f"/{self._device.serial}/awgs/{awg}/sequencer/status"
        tik = time.time()
        while self.get(node):
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise Exception("Program upload timed out!")
        print(f"Sequencer status: {'Uploaded' if not self.get(node) else 'FAILED!!'}")
