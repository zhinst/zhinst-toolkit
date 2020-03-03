import numpy as np

from .base import BaseInstrument
from .awg_core import AWGCore
from .tools import ZHTKException


class UHFQA(BaseInstrument):
    """
    High-level controller for UHFQA. Inherits from BaseInstrument and defines 
    UHFQA specific methods. The property awg_connection accesses the 
    connection's awg module and is used in the AWG core as 
    awg._parent._awg_module

    The UHFQA has one awg core and ten ReadoutChannels that can  be accessed as 
    properties of the object.

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "uhfqa", serial, **kwargs)
        self._awg = AWG(self, 0)
        self._channels = [ReadoutChannel(self, i) for i in range(10)]

    def write_crottalk_matrix(self, matrix):
        rows, cols = matrix.shape
        assert rows <= 10
        assert cols <= 10
        for r in range(rows):
            for c in range(cols):
                self._set(f"qas/0/crosstalk/rows/{r}/cols/{c}", matrix[r, c])

    def enable_readout_channels(self, channels):
        for i in channels:
            assert i in range(10)
            self.channels[i].enable()

    def disable_readout_channels(self, channels):
        for i in channels:
            assert i in range(10)
            self.channels[i].disable()

    def _init_settings(self):
        settings = [
            ("awgs/0/single", 1),
        ]
        self._set(settings)

    @property
    def awg(self):
        return self._awg

    @property
    def channels(self):
        return self._channels

    @property
    def _awg_connection(self):
        self._check_connected()
        return self._controller._connection.awg_module


class AWG(AWGCore):
    """
    Device-specific AWG for UHFQA with properties like ouput or gains and 
    sequence specific settings for the UHFQA. Inherits from AWGCore.

    """

    def __init__(self, parent, index):
        super().__init__(parent, index)
        self._output = "off"
        self._gains = (1.0, 1.0)

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
        self._parent._set(f"sigouts/*/on", value)

    @property
    def gains(self):
        return self._gains

    @gains.setter
    def gains(self, gains):
        assert len(gains) == 2
        for g in gains:
            assert abs(g) <= 1
        self._gains = gains
        self._parent._set(f"awgs/0/outputs/0/amplitude", gains[0])
        self._parent._set(f"awgs/0/outputs/1/amplitude", gains[1])

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
                raise ZHTKException(
                    f"Sequence type {t} must be one of {allowed_sequences}!"
                )
            # apply settings depending on sequence type
            if t == "CW Spectroscopy":
                self._apply_cw_settings()
            if t == "Pulsed Spectroscopy":
                self._apply_pulsed_settings()
            if t == "Readout":
                self._apply_readout_settings()

        # apply settings dependent on trigger type
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self._apply_trigger_settings()

    def _apply_cw_settings(self):
        settings = [
            ("sigouts/0/enables/0", 1),
            ("sigouts/1/enables/1", 1),
            ("sigouts/0/amplitudes/0", 1),
            ("sigouts/1/amplitudes/1", 1),
            ("qas/0/integration/mode", 1),
        ]
        self._parent._set(settings)

    def _apply_pulsed_settings(self):
        settings = [
            ("sigouts/*/enables/*", 0),
            ("sigouts/*/amplitudes/*", 0),
            ("awgs/0/outputs/*/mode", 1),
            ("qas/0/integration/mode", 1),
        ]
        self._parent._set(settings)

    def _apply_readout_settings(self):
        settings = [
            ("sigouts/*/enables/*", 0),
            ("awgs/0/outputs/*/mode", 0),
            ("qas/0/integration/mode", 0),
        ]
        self._parent._set(settings)

    def _apply_trigger_settings(self):
        settings = [
            ("/awgs/0/auxtriggers/*/channel", 0),
            ("/awgs/0/auxtriggers/*/slope", 1),
        ]
        self._parent._set(settings)

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
                raise ZHTKException("No readout channels are enabled!")
        else:
            raise ZHTKException("AWG Sequence type needs to be 'Readout'")

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
    def index(self):
        return self._index

    @property
    def enabled(self):
        return self._enabled

    def enable(self):
        self._enabled = True
        self._set_int_weights()

    def disable(self):
        self._enabled = False
        self._reset_int_weights()

    @property
    def readout_frequency(self):
        return self._readout_frequency

    @readout_frequency.setter
    def readout_frequency(self, freq):
        assert freq > 0
        self._readout_frequency = freq
        self._set_int_weights()

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
        return np.angle(self._parent._get(f"qas/0/rotations/{self._index}"), deg=True)

    @rotation.setter
    def rotation(self, rot):
        c = np.exp(1j * np.deg2rad(rot))
        self._parent._set(f"qas/0/rotations/{self._index}", c)

    @property
    def threshold(self):
        return self._parent._get(f"qas/0/thresholds/{self._index}/level")

    @threshold.setter
    def threshold(self, th):
        self._parent._set(f"qas/0/thresholds/{self._index}/level", th)

    @property
    def result(self):
        return self._parent._get(f"qas/0/result/data/{self._index}/wave")

    def _reset_int_weights(self):
        l = self._parent._get("qas/0/integration/length")
        node = f"/qas/0/integration/weights/"
        self._parent._set(node + f"{self._index}/real", np.zeros(l))
        self._parent._set(node + f"{self._index}/imag", np.zeros(l))

    def _set_int_weights(self):
        l = self._parent._get("qas/0/integration/length")
        freq = self.readout_frequency
        node = f"/qas/0/integration/weights/{self._index}/"
        self._parent._set(node + "real", self._demod_weights(l, freq, 0))
        self._parent._set(node + "imag", self._demod_weights(l, freq, 90))

    def _demod_weights(self, length, freq, phase):
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

