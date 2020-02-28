import json
import time

from .BaseController import BaseController
from ..helpers import Waveform, Compiler


"""
AWG specific controller.

Controller for all devices that have at least one AWG (i.e. HDAWG, UHFQA, UHFAWG).

"""


class AWGController(BaseController):
    def __init__(self, name, device_type, serial, **kwargs):
        super().__init__(name, device_type, serial, **kwargs)
        self._compiler = Compiler()
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

