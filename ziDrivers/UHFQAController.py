import numpy as np

from .controller import Controller, AWGWrapper
from .connection import ZIDeviceConnection


"""
High-level controller for UHFQA.

"""


class UHFQAController:
    def __init__(self):
        super().__init__()
        self.__name, self.__index = ("uhfqa0", 0)
        self.type = "uhfqa"
        self._controller = Controller()

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup("connection-uhfqa.json", connection=connection)

    def connect_device(self, address, interface):
        self._controller.connect_device(self.__name, address, interface)
        self.awg = AWG(self, self.__name, self.__index)
        self.channels = [ReadoutChannel(self, i) for i in range(10)]

    # device specific methods
    def write_crottalk_matrix(self, matrix):
        rows, cols = matrix.shape
        assert rows <= 10
        assert cols <= 10
        for r in range(rows):
            for c in range(cols):
                self._controller.set(f"qas/0/crosstalk/rows/{r}/cols/{c}", matrix[r, c])

    def enable_readout_channels(self, channels):
        for i in channels:
            assert i in range(10)
            self.channels[i].enable()

    def disable_readout_channels(self, channels):
        for i in channels:
            assert i in range(10)
            self.channels[i].disable()

    # wrap around get and set of Controller
    def set(self, *args):
        self._controller.set(self.__name, *args)

    def get(self, command, valueonly=True):
        return self._controller.get(self.__name, command, valueonly=valueonly)


"""
Device specific AWG for UHFQA.

"""


class AWG(AWGWrapper):
    def __init__(self, parent, name, index):
        super().__init__(parent, name, index)
        self._output = "off"
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
        self._parent.set(f"sigouts/*/on", value)

    def _apply_sequence_settings(self, **kwargs):
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
            # apply settings depending on sequence type
            if t == "CW Spectroscopy":
                self.__apply_cw_settings()
            if t == "Pulsed Spectroscopy":
                self.__apply_pulsed_settings()
            if t == "Readout":
                self.__apply_readout_settings()

        # apply settings dependent on trigger type
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self._parent.set("/awgs/0/auxtriggers/*/channel", 0)
                self._parent.set("/awgs/0/auxtriggers/*/slope", 1)

    def __apply_cw_settings(self):
        self._parent.set("sigouts/0/enables/0", 1)
        self._parent.set("sigouts/1/enables/1", 1)
        self._parent.set("sigouts/0/amplitudes/0", 1)
        self._parent.set("sigouts/1/amplitudes/1", 1)
        self._parent.set("qas/0/integration/mode", 1)

    def __apply_pulsed_settings(self):
        self._parent.set("sigouts/*/enables/*", 0)
        self._parent.set("sigouts/*/amplitudes/*", 0)
        self._parent.set("awgs/0/outputs/*/mode", 1)
        self._parent.set("qas/0/integration/mode", 1)

    def __apply_readout_settings(self):
        self._parent.set("sigouts/*/enables/*", 0)
        self._parent.set("awgs/0/outputs/*/mode", 0)
        self._parent.set("qas/0/integration/mode", 0)

    def update_readout_params(self):
        if self.sequence_params["sequence_type"] == "Readout":
            if any([ch.enabled for ch in self._parent.channels]):
                freqs = list()
                amps = list()
                phases = list()
                for ch in self._parent.channels:
                    if ch.enabled:
                        freqs.append(ch.readout_frequency)
                        amps.append(ch.readout_amplitude)
                        phases.append(ch.phase_shift)
                self.set_sequence_params(
                    readout_frequencies=freqs,
                    readout_amplitudes=amps,
                    phase_shifts=phases,
                )
            else:
                raise Exception("No readout channels are enabled!")
        else:
            raise Exception("AWG Sequence type needs to be 'Readout'")

    def compile(self):
        if self.sequence_params["sequence_type"] == "Readout":
            self.update_readout_params()
        super().compile()


"""
Readout Channel for UHFQA.

"""


class ReadoutChannel:
    def __init__(self, parent, index):
        assert index in range(10)
        self._index = index
        self._parent = parent
        self._enabled = False
        self._readout_frequency = 100e6
        self._readout_amplitude = 1
        self._phase_shift = 0
        self._rotation = 0
        self._threshold = 0

    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        self._enabled = True
        self.__set_int_weights()

    def disable(self):
        self._enable = False
        self.__reset_int_weights()

    @property
    def readout_frequency(self):
        return self._readout_frequency

    @readout_frequency.setter
    def readout_frequency(self, freq):
        assert freq > 0
        self._readout_frequency = freq
        self.__set_int_weights()

    @property
    def readout_amplitude(self):
        return self._readout_amplitude

    @readout_amplitude.setter
    def readout_amplitude(self, amp):
        assert abs(amp) <= 1
        self._readout_amplitude = amp

    @property
    def phase_shift(self):
        return self._phase_shift

    @phase_shift.setter
    def phase_shift(self, ph):
        assert abs(ph) <= 90
        self._phase_shift = ph

    @property
    def rotation(self):
        return np.angle(self._parent.get(f"qas/0/rotations/{self._index}"), deg=True)

    @rotation.setter
    def rotation(self, rot):
        c = np.exp(1j * np.deg2rad(rot))
        self._parent.set(f"qas/0/rotations/{self._index}", c)

    @property
    def threshold(self):
        return self._parent.get(f"qas/0/thresholds/{self._index}/level")

    @threshold.setter
    def threshold(self, th):
        self._parent.set(f"qas/0/thresholds/{self._index}/level", th)

    @property
    def result(self):
        return self._parent.get(f"qas/0/result/data/{self._index}/wave")

    def __reset_int_weights(self):
        l = self._parent.get("qas/0/integration/length")
        node = f"/qas/0/integration/weights/"
        self._parent.set(node + f"{self._index}/real", np.zeros(l))
        self._parent.set(node + f"{self._index}/imag", np.zeros(l))

    def __set_int_weights(self):
        l = self._parent.get("qas/0/integration/length")
        freq = self.readout_frequency
        node = f"/qas/0/integration/weights/{self._index}/"
        self._parent.set(node + "real", self.__demod_weights(l, freq, 0))
        self._parent.set(node + "imag", self.__demod_weights(l, freq, 90))

    def __demod_weights(self, length, freq, phase):
        assert length <= 4096
        assert freq > 0
        clk_rate = 1.8e9
        x = np.arange(0, length)
        y = np.sin(2 * np.pi * freq * x / clk_rate + np.deg2rad(phase))
        return y

    def __repr__(self):
        s = f"Readout Channel {self._index}:  {super().__repr__()}\n"
        if self._enabled:
            s += f"     readout_frequency : {self._readout_frequency}\n"
            s += f"     readout_amplitude : {self._readout_amplitude}\n"
            s += f"     phase_shift       : {self._phase_shift}\n"
            s += f"     rotation          : {self._rotation}\n"
            s += f"     threshold         : {self._threshold}\n"
        else:
            s += "      DISABLED\n"
        return s

