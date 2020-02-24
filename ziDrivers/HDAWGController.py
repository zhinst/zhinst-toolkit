import json
import time
import pathlib
import numpy as np

from .controller import Controller, AWGWrapper
from .connection import ZIDeviceConnection
from .interface import InstrumentConfiguration


class HDAWGController:
    def __init__(self):
        super().__init__()
        self.__name = "hdawg0"
        self.type = "hdawg"
        self._controller = Controller()

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup("connection-hdawg.json", connection=connection)

    def connect_device(self, address, interface):
        self._controller.connect_device(self.__name, address, interface)
        self.awgs = []
        for i in range(4):
            self.awgs.append(AWGWrapper(self, self.__name, i))

    ####################################################
    # device specific methods

    def set_outputs(self, values):
        assert len(values) == 4
        for i, v in enumerate(values):
            self.set_output(i, v)

    def set_output(self, awg, value):
        if value == "on":
            value = 1
        if value == "off":
            value = 0
        self._controller.set(f"sigouts/{2 * awg}/on", value)
        self._controller.set(f"sigouts/{2 * awg + 1}/on", value)

    def enable_iq_modulation(self, awg):
        if awg == "all":
            [self.enable_iq_modulation(i) for i in range(4)]
        else:
            settings = [
                (f"awgs/{awg}/outputs/0/modulation/mode", 1),  # modulation: sine 11
                (f"awgs/{awg}/outputs/1/modulation/mode", 2),  # modulation: sine 22
                (f"sines/{2 * awg}/oscselect", 4 * awg),  # select osc N for awg N
                (f"sines/{2 * awg + 1}/oscselect", 4 * awg),  # select osc N for awg N
                (
                    f"sines/{2 * awg + 1}/phaseshift",
                    90,
                ),  # 90 deg phase shift on second channel
            ]
            self.set(settings)

    def set_modulation_frequencies(self, frequencies):
        assert len(frequencies) <= 4
        [self.set_modulation_frequency(i, f) for i, f in enumerate(frequencies)]

    def set_modulation_frequency(self, awg, freq):
        assert freq > 0
        self._controller.set(f"oscs/{awg}/freq", freq)

    def set_modulation_phases(self, phases):
        assert len(phases) <= 4
        for i, p in enumerate(phases):
            self.set_modulation_phase(i, p)

    def set_modulation_phase(self, awg, p):
        self._controller.set(f"sines/{2 * awg + 1}/phaseshift", p)

    def set_modulation_gains(self, gains):
        assert len(gains) <= 4
        [self.set_modulation_gain(i, g) for i, g in enumerate(gains)]

    def set_modulation_gain(self, awg, g):
        assert len(g) == 2
        self._controller.set(f"awgs/{awg}/outputs/0/gains/0", g[0])
        self._controller.set(f"awgs/{awg}/outputs/1/gains/1", g[1])

    # apply device settings depending on sequence settings
    def __apply_sequence_settings(self, awg, **kwargs):
        if "sequence_type" in kwargs.keys():
            t = kwargs["sequence_type"]
            allowed_sequences = [
                "Simple",
                "Readout",
                "CW Spectroscopy",
                "Pulsed Spectroscopy",
                "Custom",
            ]
            if t not in allowed_sequences:
                raise Exception(
                    f"Sequence type {t} must be one of {allowed_sequences}!"
                )
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self.__apply_trigger_settings(awg)

    def __apply_trigger_settings(self, awg):
        self._controller.set(f"/awgs/{awg}/auxtriggers/*/channel", 2 * awg)
        self._controller.set(f"/awgs/{awg}/auxtriggers/*/slope", 1)  # rise

    ####################################################
    # overwrite old stuff

    # overwrite set and get with device name
    def set(self, *args):
        self._controller.set(self.__name, *args)

    def get(self, command, valueonly=True):
        return self._controller.get(self.__name, command, valueonly=valueonly)

