import numpy as np

from .tools import AWGController, AWGCore, ZIDeviceConnection


"""
High-level controller for UHFQA.

"""


class UHFLI:
    def __init__(self, name):
        self._name = name
        self._controller = AWGController()

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup(connection=connection)

    def connect_device(self, address, interface):
        self._controller.connect_device(self.name, "uhfqa", address, interface)
        self.awg = AWG(self, self.name, 0)
        self._init_settings()

    @property
    def name(self):
        return self._name

    # device specific methods

    def _init_settings(self):
        settings = [
            ("awgs/0/single", 1),
        ]
        self.set(settings)

    # wrap around get and set of Controller
    def set(self, *args):
        self._controller.set(self.name, *args)

    def get(self, command, valueonly=True):
        return self._controller.get(self.name, command, valueonly=valueonly)

    def get_nodetree(self, prefix, **kwargs):
        return self._controller.get_nodetree(prefix, **kwargs)


"""
Device specific AWG for UHFLI.

"""


class AWG(AWGCore):
    def __init__(self, parent, name, index):
        super().__init__(parent, name, index)
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
        self._parent.set(f"sigouts/*/on", value)

    @property
    def gains(self):
        return self._gains

    @gains.setter
    def gains(self, gains):
        assert len(gains) == 2
        for g in gains:
            assert abs(g) <= 1
        self._gains = gains
        self._parent.set(f"awgs/0/outputs/0/amplitude", gains[0])
        self._parent.set(f"awgs/0/outputs/1/amplitude", gains[1])

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
        self._parent.set("sigouts/0/enables/0", 1)
        self._parent.set("sigouts/1/enables/1", 1)
        self._parent.set("sigouts/0/amplitudes/0", 1)
        self._parent.set("sigouts/1/amplitudes/1", 1)
        self._parent.set("qas/0/integration/mode", 1)

    def _apply_pulsed_settings(self):
        self._parent.set("sigouts/*/enables/*", 0)
        self._parent.set("sigouts/*/amplitudes/*", 0)
        self._parent.set("awgs/0/outputs/*/mode", 1)
        self._parent.set("qas/0/integration/mode", 1)

    def _apply_readout_settings(self):
        self._parent.set("sigouts/*/enables/*", 0)
        self._parent.set("awgs/0/outputs/*/mode", 0)
        self._parent.set("qas/0/integration/mode", 0)

    def _apply_trigger_settings(self):
        self._parent.set("/awgs/0/auxtriggers/*/channel", 0)
        self._parent.set("/awgs/0/auxtriggers/*/slope", 1)

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

