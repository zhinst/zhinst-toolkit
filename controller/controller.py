import json
import time

from .baseController import BaseController
from ..helpers import SequenceProgram, Waveform, Compiler


class Controller(BaseController):
    def __init__(self):
        super().__init__()
        self._compiler = Compiler()

    def connect_device(self, name, address):
        super().connect_device(name, address)
        for dev in self._instrument_config.instruments[0].setup:
            if dev.name == name:
                self._compiler.add_device(dev)

    def awg_compile(self, name, awg):
        self._connection.awg_module.update(index=awg, device=self._devices[name].serial)
        if self._compiler.sequence_type(name, awg) == "Simple":
            buffer_lengths = [
                w.buffer_length for w in self._devices[name].awgs[awg].waveforms
            ]
            self._compiler.set_parameter(name, awg, buffer_lengths=buffer_lengths)
        self.__update_awg_program(name, awg)
        program = self._devices[name].awgs[awg].get_program()
        self._connection.awg_module.set("compiler/sourcestring", program)
        while self._connection.awg_module.get_int("compiler/status") == -1:
            time.sleep(0.1)
        if self._connection.awg_module.get_int("compiler/status") == 1:
            raise Exception(
                "Upload failed: \n"
                + self._connection.awg_module.get_string("compiler/statusstring")
            )
        if self._connection.awg_module.get_int("compiler/status") == 2:
            raise Warning(
                "Compiled with warning: \n"
                + self._connection.awg_module.get_string("compiler/statusstring")
            )
        if self._connection.awg_module.get_int("compiler/status") == 2:
            print("Compilation successful")
        self.__wait_upload_done(name, awg)

    def awg_run(self, name, awg):
        self.set(name, f"/awgs/{awg}/enable", 1)
        print(f"{name}: Started AWG {awg}!")

    def awg_stop(self, name, awg):
        self.set(name, f"/awgs/{awg}/enable", 0)
        print(f"{name}: Stopped AWG {awg}!")

    def awg_is_running(self, name, awg):
        return bool(
            self._connection.awg_module.get_int(
                "awg/enable", index=awg, device=self._devices[name].serial
            )
        )

    def awg_queue_waveform(self, name, awg, waveform: Waveform):
        if self._compiler.sequence_type(name, awg) != "Simple":
            raise Exception("Waveform upload only possible for 'Simple' sequence!")
        self._devices[name].awgs[awg].waveforms.append(waveform)
        print(
            f"current length of queue: {len(self._devices[name].awgs[awg].waveforms)}"
        )

    def awg_upload_waveforms(self, name, awg):
        waveform_data = [w.data for w in self._devices[name].awgs[awg].waveforms]
        self.awg_compile(name, awg)
        nodes = [f"awgs/{awg}/waveform/waves/{i}" for i in range(len(waveform_data))]
        self.set(name, zip(nodes, waveform_data))
        time.sleep(0.5)  # make sure waveform uplaod finished, any other way??
        self._devices[name].awgs[awg].reset_waveforms()

    def awg_set_sequence_params(self, name, awg, **kwargs):
        self._compiler.set_parameter(name, awg, **kwargs)
        self.__update_awg_program(name, awg)

    def awg_list_params(self, name, awg):
        return self._compiler.list_params(name, awg)

    def __update_awg_program(self, name, awg):
        program = self._compiler.get_program(name, awg)
        self._devices[name].awgs[awg].set_program(program)

    def __wait_upload_done(self, name, awg, timeout=10):
        time.sleep(0.01)
        self._connection.awg_module.update(device=self._devices[name].serial, index=awg)
        tik = time.time()
        while self._connection.awg_module.get_int("/elf/status") == 2:
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise Exception("Program upload timed out!")
        status = self._connection.awg_module.get_int("/elf/status")
        print(f"{name}: Sequencer status: {'Uploaded' if status == 0 else 'FAILED!!'}")
