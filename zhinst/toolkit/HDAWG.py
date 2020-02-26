import numpy as np

from .AWG import AWGController, AWGCore
from .connection import ZIDeviceConnection


"""
High-level controller for HDAWG.

"""


class HDAWG:
    def __init__(self):
        self.__name = "hdawg0"
        self._controller = AWGController()

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup("connection-hdawg.json", connection=connection)

    def connect_device(self, address, interface):
        self._controller.connect_device(self.__name, address, interface)
        self.awgs = [AWG(self, self.__name, i) for i in range(4)]
        self.__init_settings()

    # device specific methods
    def set_outputs(self, values):
        assert len(values) == 4
        [self.awgs[i].set_output(v) for i, v in enumerate(values)]

    def set_modulation_frequencies(self, frequencies):
        assert len(frequencies) <= 4
        [self.awgs[i].set_modulation_frequency(f) for i, f in enumerate(frequencies)]

    def set_modulation_phases(self, phases):
        assert len(phases) <= 4
        [self.awgs[i].set_modulation_phase(p) for i, p in enumerate(phases)]

    def set_modulation_gains(self, gains):
        assert len(gains) <= 4
        [self.awgs[i].set_modulation_gain(g) for i, g in enumerate(gains)]

    def __init_settings(self):
        settings = [
            ("awgs/*/single", 1),
        ]
        self.set(settings)

    # wrap around get and set of Controller
    def set(self, *args):
        self._controller.set(self.__name, *args)

    def get(self, command, valueonly=True):
        return self._controller.get(self.__name, command, valueonly=valueonly)


"""
AWG specific to HDAWG.

"""


class AWG(AWGCore):
    def __init__(self, parent, name, index):
        super().__init__(parent, name, index)
        self._output = "off"
        self._iq_modulation = False
        self._modulation_freq = 10e6
        self._modulation_phase_shift = 0
        self._modulation_gains = (1.0, 1.0)

    @property
    def output(self):
        return "on" if self._output else "off"

    @output.setter
    def output(self, value):
        if value == "on":
            value = 1
        if value == "off":
            value = 0
        self._output = value
        self._parent.set(f"sigouts/{2 * self._index}/on", value)
        self._parent.set(f"sigouts/{2 * self._index + 1}/on", value)

    def enable_iq_modulation(self):
        self._iq_modulation = True
        i = self._index
        settings = [
            (f"awgs/{i}/outputs/0/modulation/mode", 1),  # modulation: sine 11
            (f"awgs/{i}/outputs/1/modulation/mode", 2),  # modulation: sine 22
            (f"sines/{2 * i}/oscselect", 4 * i),  # select osc N for awg N
            (f"sines/{2 * i + 1}/oscselect", 4 * i),  # select osc N for awg N
            (f"sines/{2 * i + 1}/phaseshift", 90,),  # 90 deg phase shift
        ]
        self._parent.set(settings)

    def disable_iq_modulation(self):
        self._iq_modulation = False
        i = self._index
        settings = [
            (f"awgs/{i}/outputs/0/modulation/mode", 0),  # modulation: sine 11
            (f"awgs/{i}/outputs/1/modulation/mode", 0),  # modulation: sine 22
            (f"sines/{2 * i + 1}/phaseshift", 0,),  # 90 deg phase shift
        ]
        self._parent.set(settings)

    @property
    def modulation_frequency(self):
        return self._modulation_freq

    @modulation_frequency.setter
    def modulation_frequency(self, freq):
        assert freq > 0
        self._modulation_freq = freq
        self._parent.set(f"oscs/{4 * self._index}/freq", freq)

    @property
    def modulation_phase_shift(self):
        return self._modulation_phase_shift

    @modulation_phase_shift.setter
    def modulation_phase_shift(self, ph):
        self._modulation_phase_shift = ph
        self._parent.set(f"sines/{2 * self._index + 1}/phaseshift", 90 + ph)

    @property
    def modulation_gains(self):
        return self._modulation_gains

    @modulation_gains.setter
    def modulation_gains(self, gains):
        assert len(gains) == 2
        for g in gains:
            assert abs(g) <= 1
        self._modulation_gains = gains
        self._parent.set(f"awgs/{self._index}/outputs/0/gains/0", gains[0])
        self._parent.set(f"awgs/{self._index}/outputs/1/gains/1", gains[1])

    def _apply_sequence_settings(self, **kwargs):
        if "sequence_type" in kwargs.keys():
            t = kwargs["sequence_type"]
            allowed_sequences = [
                "None",
                "Simple",
                "Rabi",
                "T1",
                "T2*",
                "Custom",
            ]
            if t not in allowed_sequences:
                raise Exception(
                    f"Sequence type {t} must be one of {allowed_sequences}!"
                )
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self.__apply_trigger_settings()

    def __apply_trigger_settings(self):
        i = self._index
        self._parent.set(f"/awgs/{i}/auxtriggers/*/channel", 2 * i)
        self._parent.set(f"/awgs/{i}/auxtriggers/*/slope", 1)  # rise

    def __repr__(self):
        s = f"{super().__repr__()}"
        if self._iq_modulation:
            s += f"      IQ Modulation ENABLED:\n"
            s += f"         frequency   : {self._modulation_freq}\n"
            s += f"         phase_shift : {self._modulation_phase_shift}\n"
            s += f"         gains       : {self._modulation_gains}\n"
        else:
            s += f"      IQ Modulation DISABLED\n"
        return s

