import time
import numpy as np
from typing import List, Dict

from .base import ToolkitError, BaseInstrument
from zhinst.toolkit.control.node_tree import Parameter

MAPPINGS = {
    "time": {
        0: "1.80 GHz",
        1: "900 MHz",
        2: "450 MHz",
        3: "225 MHz",
        4: "113 MHz",
        5: "56.2 MHz",
        6: "28.1 MHz",
        7: "14.0 MHz",
        8: "7.03 MHz",
        9: "3.50 MHz",
        10: "1.75 MHz",
        11: "880 kHz",
        12: "440 kHz",
        13: "220 kHz",
        14: "110 kHz",
        15: "54.9 kHz",
        16: "27.5 kHz",
    },
    "trigenable": {0: "on", 1: "off"},
    "trigrising": {0: "on", 1: "off"},
    "trigfalling": {0: "on", 1: "off"},
    "trigholdoffmode": {0: "time", 1: "events"},
    "trigslope": {0: "None", 1: "rising", 2: "falling", 3: "both"},
    "triggate_inputselect": {
        0: "trigin3high",
        1: "trigin3low",
        2: "trigin4high",
        3: "trigin4low",
    },
    "stream_rate": {
        6: "28.1 MHz",
        7: "14.0 MHz",
        8: "7.03 MHz",
        9: "3.50 MHz",
        10: "1.75 MHz",
        11: "880 kHz",
        12: "440 kHz",
        13: "220 kHz",
        14: "110 kHz",
        15: "54.9 kHz",
        16: "27.5 kHz",
    },
    "channel": {1: "channel 1", 2: "channel 2", 3: "both"},
    "averager_resamplingmode": {0: "linear", 1: "PCHIP"},
    "fft_window": {0: "rectangular", 1: "hann", 2: "hamming", 3: "blackman"},
    "mode": {0: "pass-through", 1: "moving average", 3: "fft"},
    "save_fileformat": {0: "matlab", 1: "csv", 2: "zview", 3: "sxm", 4: "hdf5"},
}


class ScopeModule:
    def __init__(self, parent: BaseInstrument) -> None:
        self._parent = parent
        self._module = None
        self._result = None

    def _setup(self) -> None:
        self._module = self._parent._controller._connection.scope_module
        # add all parameters from module's nodetree
        module_nodetree = self._module.get_nodetree("*")
        for k, v in module_nodetree.items():
            name = k[1:].replace("/", "_")
            mapping = MAPPINGS[name] if name in MAPPINGS.keys() else None
            setattr(self, name, Parameter(self, v, device=self, mapping=mapping))
        # add all scope parameters from parent's nodetree
        parent_nodetree = self._parent._controller.get_nodetree(
            f"{self._parent.serial}/scopes/0/*"
        )
        for k, v in parent_nodetree.items():
            k = k.lower().replace(f"{self._parent.serial}/scopes/0/", "")
            name = k[1:].replace("/", "_")
            v["Node"] = v["Node"].lower().replace(f"{self._parent.serial}/", "")
            mapping = MAPPINGS[name] if name in MAPPINGS.keys() else None
            if name in [
                "channels_0_inputselect",
                "channels_1_inputselect",
                "trigchannel",
            ]:
                mapping = {
                    int(k): v.replace(
                        ". Requires an installed digitizer (DIG) option.", ""
                    )
                    for k, v in v["Options"].items()
                }
            setattr(
                self, name, Parameter(self, v, device=self._parent, mapping=mapping)
            )
        self._init_settings()

    def _set(self, *args):
        if self._module is None:
            raise ToolkitError("This DAQ is not connected to a dataAcquisitionModule!")
        return self._module.set(*args)

    def _get(self, *args, valueonly: bool = True):
        if self._module is None:
            raise ToolkitError("This DAQ is not connected to a dataAcquisitionModule!")
        data = self._module.get(*args)
        return list(data.values())[0][0] if valueonly else data

    def _init_settings(self):
        pass

    def measure(self):
        self._module.subscribe(f"{self._parent.serial}/scopes/0/wave")
        self._module.execute()
        self._parent._set(f"/scopes/0/enable", 1)
        while not self._get("records"):
            time.sleep(0.001)
        self._parent._set(f"/scopes/0/enable", 0)
        self._result = ScopeWaves(self._module.read(flat=True), self._parent.serial)
        self._module.finish()
        return self._result


class ScopeWaves:
    def __init__(self, data, serial):
        self._wave_data = data[f"{serial}/scopes/0/wave"][0][0]
        self._waves = self._wave_data["wave"]
        self._time = np.linspace(
            0, self._wave_data["dt"] * self._wave_data["totalsamples"]
        )

    @property
    def time(self):
        return self._time

    @property
    def wave1(self):
        return self._waves[0]

    @property
    def wave2(self):
        try:
            return self._waves[1]
        except IndexError:
            return None
