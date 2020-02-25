import json
import time
from abc import ABC, abstractmethod

from .baseController import BaseController
from .helpers import Waveform, Compiler


class Controller(BaseController):
    def __init__(self):
        super().__init__()
        self._compiler = Compiler()

    def connect_device(self, name, address, interface):
        super().connect_device(name, address, interface)
        for dev in self._instrument_config.instruments[0].setup:
            if dev.name == name:
                self._compiler.add_device(dev)

    def awg_compile(self, name, awg):
        self._connection.awg_module.update(device=self._devices[name].serial)
        self._connection.awg_module.update(index=awg)
        if self._compiler.sequence_type(name, awg) == "Simple":
            buffer_lengths = [
                w.buffer_length for w in self._devices[name].awgs[awg].waveforms
            ]
            self._compiler.set_parameter(name, awg, buffer_lengths=buffer_lengths)
        self.__update_awg_program(name, awg)
        program = self._devices[name].awgs[awg].program
        # if program == self._connection.awg_module.get_string("compiler/sourcestring"):
        #     print("Same program! Did nothing...")
        #     return
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
        if self._connection.awg_module.get_int("compiler/status") == 0:
            print("Compilation successful")
        self.__wait_upload_done(name, awg)

    def awg_run(self, name, awg):
        self.set(name, f"/awgs/{awg}/enable", 1)
        print(f"{name}: Started AWG {awg}!")

    def awg_stop(self, name, awg):
        self.set(name, f"/awgs/{awg}/enable", 0)
        print(f"{name}: Stopped AWG {awg}!")

    def awg_is_running(self, name, awg):
        return self.get(name, f"/awgs/{awg}/enable")

    def awg_queue_waveform(self, name, awg, data=([], [])):
        if self._compiler.sequence_type(name, awg) != "Simple":
            raise Exception("Waveform upload only possible for 'Simple' sequence!")
        waveform = Waveform(data[0], data[1])
        self._devices[name].awgs[awg].waveforms.append(waveform)
        print(
            f"current length of queue: {len(self._devices[name].awgs[awg].waveforms)}"
        )

    def awg_compile_and_upload_waveforms(self, name, awg):
        self.awg_compile(name, awg)
        self.awg_upload_waveforms(name, awg)

    def awg_upload_waveforms(self, name, awg):
        waveform_data = [w.data for w in self._devices[name].awgs[awg].waveforms]
        nodes = [f"awgs/{awg}/waveform/waves/{i}" for i in range(len(waveform_data))]
        tok = time.time()
        self.set(name, zip(nodes, waveform_data))
        tik = time.time()
        print(f"Upload of {len(waveform_data)} waveforms took {tik - tok} s")

    def awg_replace_waveform(self, name, awg, data=([], []), index=0):
        if index not in range(len(self._devices[name].awgs[awg].waveforms)):
            raise Exception("Index out of range!")
        self._devices[name].awgs[awg].waveforms[index].replace_data(data[0], data[1])

    def awg_reset_queue(self, name, awg):
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
        print(
            f"{name}: Sequencer status: {'ELF file uploaded' if status == 0 else 'FAILED!!'}"
        )


class AWGWrapper(ABC):
    def __init__(self, parent, name, index):
        self._parent = parent
        self._controller = self._parent._controller
        self._name = name
        self._index = index

    def __repr__(self):
        params = self.sequence_params["sequence_parameters"]
        s = f"{self._name}: {super().__repr__()}\n"
        s += f"    parent  : {self._parent}\n"
        s += f"    index   : {self._index}\n"
        s += f"    sequence: \n"
        s += f"           type: {self.sequence_params['sequence_type']}\n"
        for i in params.items():
            s += f"            {i}\n"
        return s

    def run(self):
        self._controller.awg_run(self._name, self._index)

    def stop(self):
        self._controller.awg_stop(self._name, self._index)

    def compile(self):
        self._controller.awg_compile(self._name, self._index)

    def reset_queue(self):
        self._controller.awg_reset_queue(self._name, self._index)

    def queue_waveform(self, wave1, wave2):
        self._controller.awg_queue_waveform(
            self._name, self._index, data=(wave1, wave2)
        )

    def replace_waveform(self, wave1, wave2, i=0):
        self._controller.awg_replace_waveform(
            self._name, self._index, data=(wave1, wave2), index=i
        )

    def upload_waveforms(self):
        self._controller.awg_upload_waveforms(self._name, self._index)

    def compile_and_upload_waveforms(self):
        self._controller.awg_compile_and_upload_waveforms(self._name, self._index)

    def set_sequence_params(self, **kwargs):
        self._apply_sequence_settings(**kwargs)
        self._controller.awg_set_sequence_params(self._name, self._index, **kwargs)

    @abstractmethod
    def _apply_sequence_settings(self, **kwargs):
        pass

    @property
    def is_running(self):
        return self._controller.awg_is_running(self._name, self._index)

    @property
    def sequence_params(self):
        return self._controller.awg_list_params(self._name, self._index)
