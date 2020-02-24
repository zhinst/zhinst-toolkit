import json
import time

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
        self._connection.awg_module.update(index=awg, device=self._devices[name].serial)
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


class AWGWrapper:
    def __init__(self, parent, name, index):
        self.__parent = parent
        self.__controller = self.__parent._controller
        self.__name = name
        self.__index = index

    def run(self):
        self.__controller.awg_run(self.__name, self.__index)

    def stop(self):
        self.__controller.awg_stop(self.__name, self.__index)

    def compile(self):
        self.__controller.awg_compile(self.__name, self.__index)

    def reset_queue(self):
        self.__controller.awg_reset_queue(self.__name, self.__index)

    def queue_waveform(self, wave1, wave2):
        self.__controller.awg_queue_waveform(
            self.__name, self.__index, data=(wave1, wave2)
        )

    def replace_waveform(self, wave1, wave2, i=0):
        self.__controller.awg_replace_waveform(
            self.__name, self.__index, data=(wave1, wave2), index=i
        )

    def upload_waveforms(self):
        self.__controller.awg_upload_waveforms(self.__name, self.__index)

    def compile_and_upload_waveforms(self):
        self.__controller.awg_compile_and_upload_waveforms(self.__name, self.__index)

    def set_sequence_params(self, **kwargs):
        self.__parent._apply_sequence_settings(**kwargs)
        self.__controller.awg_set_sequence_params(self.__name, self.__index, **kwargs)

    def is_running(self):
        return self.__controller.awg_is_running(self.__name, self.__index)

    def list_params(self):
        return self.__controller.awg_list_params(self.__name, self.__index)
