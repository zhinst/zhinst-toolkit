import json
import time
from abc import ABC, abstractmethod

from .BaseController import BaseController
from .helpers import Waveform, Compiler


"""
AWG Core representation.

Wrapper around AWGController with specific attributes for an AWG Core:
- a parent instrument
- an index
- a name (of the controller, e.g. "hdawg0")
- pretty __repr__() method
- wrap around controller methods with name and index for onvenience

"""


class AWGCore(ABC):
    def __init__(self, parent, name, index):
        self._parent = parent
        self._name = name
        self._index = index

    @property
    def name(self):
        return self._name + str(self._index)

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
        self._parent._controller.awg_run(self._index)

    def stop(self):
        self._parent._controller.awg_stop(self._index)

    def compile(self):
        self._parent._controller.awg_compile(self._index)

    def reset_queue(self):
        self._parent._controller.awg_reset_queue(self._index)

    def queue_waveform(self, wave1, wave2):
        self._parent._controller.awg_queue_waveform(self._index, data=(wave1, wave2))

    def replace_waveform(self, wave1, wave2, i=0):
        self._parent._controller.awg_replace_waveform(
            self._index, data=(wave1, wave2), index=i
        )

    def upload_waveforms(self):
        self._parent._controller.awg_upload_waveforms(self._index)

    def compile_and_upload_waveforms(self):
        self._parent._controller.awg_compile_and_upload_waveforms(self._index)

    def set_sequence_params(self, **kwargs):
        self._apply_sequence_settings(**kwargs)
        self._parent._controller.awg_set_sequence_params(self._index, **kwargs)

    @abstractmethod
    def _apply_sequence_settings(self, **kwargs):
        pass

    @property
    def is_running(self):
        return self._parent._controller.awg_is_running(self._index)

    @property
    def sequence_params(self):
        return self._parent._controller.awg_list_params(self._index)


"""
AWG specific controller.

Controller for all devices that have at least one AWG (i.e. HDAWG, UHFQA, UHFAWG).

"""


class AWGController(BaseController):
    def __init__(self):
        super().__init__()
        self._compiler = Compiler()

    def connect_device(self, name, device_type, address, interface):
        super().connect_device(name, device_type, address, interface)
        self._compiler.add_device(self._device)

    def awg_compile(self, awg):
        self._connection.awg_module.update(device=self._device.serial)
        self._connection.awg_module.update(index=awg)
        if self._compiler.sequence_type(awg) == "Simple":
            buffer_lengths = [w.buffer_length for w in self._device.awgs[awg].waveforms]
            self._compiler.set_parameter(awg, buffer_lengths=buffer_lengths)
        self._update_awg_program(awg)
        program = self._device.awgs[awg].program
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
        self._wait_upload_done(awg)

    def awg_run(self, awg):
        self.set(f"/awgs/{awg}/enable", 1)
        print(f"{self._device.name}: Started AWG {awg}!")

    def awg_stop(self, awg):
        self.set(f"/awgs/{awg}/enable", 0)
        print(f"{self._device.name}: Stopped AWG {awg}!")

    def awg_is_running(self, awg):
        return self.get(f"/awgs/{awg}/enable")

    def awg_queue_waveform(self, awg, data=([], [])):
        if self._compiler.sequence_type(awg) != "Simple":
            raise Exception("Waveform upload only possible for 'Simple' sequence!")
        waveform = Waveform(data[0], data[1])
        self._device.awgs[awg].waveforms.append(waveform)
        print(f"current length of queue: {len(self._device.awgs[awg].waveforms)}")

    def awg_compile_and_upload_waveforms(self, awg):
        self.awg_compile(awg)
        self.awg_upload_waveforms(awg)

    def awg_upload_waveforms(self, awg):
        waveform_data = [w.data for w in self._device.awgs[awg].waveforms]
        nodes = [f"awgs/{awg}/waveform/waves/{i}" for i in range(len(waveform_data))]
        tok = time.time()
        self.set(zip(nodes, waveform_data))
        tik = time.time()
        print(f"Upload of {len(waveform_data)} waveforms took {tik - tok} s")

    def awg_replace_waveform(self, awg, data=([], []), index=0):
        if index not in range(len(self._device.awgs[awg].waveforms)):
            raise Exception("Index out of range!")
        self._device.awgs[awg].waveforms[index].replace_data(data[0], data[1])

    def awg_reset_queue(self, awg):
        self._device.awgs[awg].reset_waveforms()

    def awg_set_sequence_params(self, awg, **kwargs):
        self._compiler.set_parameter(awg, **kwargs)
        self._update_awg_program(awg)

    def awg_list_params(self, awg):
        return self._compiler.list_params(awg)

    def _update_awg_program(self, awg):
        program = self._compiler.get_program(awg)
        self._device.awgs[awg].set_program(program)

    def _wait_upload_done(self, awg, timeout=10):
        time.sleep(0.01)
        self._connection.awg_module.update(device=self._device.serial, index=awg)
        tik = time.time()
        while self._connection.awg_module.get_int("/elf/status") == 2:
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise Exception("Program upload timed out!")
        status = self._connection.awg_module.get_int("/elf/status")
        print(
            f"{self._device.name}: Sequencer status: {'ELF file uploaded' if status == 0 else 'FAILED!!'}"
        )

