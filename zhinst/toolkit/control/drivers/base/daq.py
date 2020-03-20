import time

from .base import ZHTKException
from control.nodetree import Parameter


MAPPINGS = {
    "edge": {1: "rising", 2: "falling", 3: "both",},
    "eventcount_mode": {0: "sample", 1: "increment"},
    "fft_window": {
        0: "rectangular",
        1: "hann",
        2: "hamming",
        3: "blackman",
        16: "exponential",
        17: "cosine",
        17: "sine",
        18: "cosine squared",
    },
    "grid_direction": {0: "forward", 1: "reverse", 2: "bidirectional",},
    "grid_mode": {1: "nearest", 2: "linear", 4: "exact",},
    "save_fileformat": {0: "matlab", 1: "csv", 2: "zview", 3: "sxm", 4: "hdf5",},
    "type": {
        0: "continuous",
        1: "edge",
        2: "dio",
        3: "pulse",
        4: "tracking",
        5: "change",
        6: "hardware",
        7: "tracking pulse",
        8: "eventcount",
    },
    "signals": {
        "demod 1 r": "/demods/0/sample.R",
        "demod 1 x": "/demods/0/sample.X",
        "demod 1 y": "/demods/0/sample.Y",
        "demod 1 theta": "/demods/0/sample.Theta",
        "frequency 1": "/demods/0/sample.Frequency",
        "demod 1 aux input 1": "/demods/0/sample.AuxIn0",
        "demod 1 aux input 2": "/demods/0/sample.AuxIn1",
        "dio 1": "/demods/0/sample.Dio",
        "demod 2 r": "/demods/1/sample.R",
        "demod 2 x": "/demods/1/sample.X",
        "demod 2 y": "/demods/1/sample.Y",
        "demod 2 theta": "/demods/1/sample.Theta",
        "frequency 2": "/demods/1/sample.Frequency",
        "demod 2 aux input 1": "/demods/1/sample.AuxIn0",
        "demod 2 aux input 2": "/demods/1/sample.AuxIn1",
        "dio 2": "/demods/1/sample.Dio",
        "imp real": "/imps/0/sample.RealZ",
        "imp imag": "/imps/0/sample.ImagZ",
        "imp abs": "/imps/0/sample.AbsZ",
        "imp theta": "/imps/0/sample.PhaseZ",
        "imp frequency": "/imps/0/sample.Frequency",
        "imp param 1": "/imps/0/sample.Param0",
        "imp param 2": "/imps/0/sample.Param1",
        "imp drive": "/imps/0/sample.Drive",
        "imp bias": "/imps/0/sample.Bias",
    },
}


class DAQModule:
    def __init__(self, parent):
        self._parent = parent
        self._module = None
        self._signals = {}
        self._results = {}

    def _setup(self):
        self._module = self._parent._controller._connection.daq_module
        # add all parameters from nodetree
        nodetree = self._module.get_nodetree("*")
        for k, v in nodetree.items():
            name = k[1:].replace("/", "_")
            mapping = MAPPINGS[name] if name in MAPPINGS.keys() else None
            setattr(self, name, Parameter(self, v, device=self, mapping=mapping))
        self._init_settings()

    def _set(self, *args):
        if self._module is None:
            raise ZHTKException("This DAQ is not connected to a dataAcquisitionModule!")
        return self._module.set(*args, device=self._parent.serial)

    def _get(self, *args, valueonly=True):
        if self._module is None:
            raise ZHTKException("This DAQ is not connected to a dataAcquisitionModule!")
        data = self._module.get(*args, device=self._parent.serial)
        return list(data.values())[0][0] if valueonly else data

    def _init_settings(self):
        self._set("preview", 1)
        self._set("historylength", 10)
        self._set("bandwidth", 0)
        self._set("hysteresis", 0.01)
        self._set("level", 0.1)
        self._set("clearhistory", 1)
        self._set("bandwidth", 0)

    def signals_add(self, signal, operation="avg"):
        if operation not in ["replace", "avg", "std"]:
            raise Exception()
        if operation == "replace":
            operation = ""
        mapping = MAPPINGS["signals"]
        if signal not in mapping.keys():
            raise ZHTKException(
                f"Unknown signal. Avalable signals are {list(mapping.keys())}"
            )
        signal_node = "/"
        signal_node += self._parent.serial
        signal_node += mapping[signal]
        signal_node += f".{operation}"
        signal_name = f"{signal} {operation}"
        if signal_node not in self.signals.values():
            self._signals[signal_name] = signal_node

    def signals_clear(self):
        self._signals = {}

    def signals_list(self):
        print("available signals:")
        for signal in MAPPINGS["signals"]:
            print(f" - '{signal}'")

    def measure(self, single=True, verbose=True, timeout=20):
        self._set("endless", int(not single))
        self._set("clearhistory", 1)
        for path in self.signals.values():
            self._module.subscribe(path)
            if verbose:
                print(f"subscribed to: {path}")
        self._module.execute()
        while not self._module.finished():
            if verbose:
                print(f"Progress: {(self._module.progress()[0] * 100):.1f}%")
            tik = time.time()
            time.sleep(0.5)
            tok = time.time()
            if tok - tik > timeout:
                raise TimeoutError()
        result = self._module.read(flat=True)
        self._module.finish()
        self._module.unsubscribe("*")
        self._get_result_from_dict(result)

    @property
    def signals(self):
        return self._signals

    @property
    def results(self):
        return self._results

    def _get_result_from_dict(self, result):
        self._results = {}
        for name, path in self.signals.items():
            path = path.lower()
            if path not in result.keys():
                raise ZHTKException()
            self._results[name] = {
                "header": result[path][0]["header"],
                "timestamp": result[path][0]["timestamp"],
                "value": result[path][0]["value"],
            }

    # here have some higher level 'measure()' mthod?? that combines subscribe read unsubscribe

    # def execute(self):
    #     self._module.execute(device=self._parent.serial)

    # def finish(self):
    #     self._module.finish(device=self._parent.serial)

    # def progress(self):
    #     return self._module.progress(device=self._parent.serial)

    # def trigger(self):
    #     self._module.trigger(device=self._parent.serial)

    # def read(self):
    #     data = self._module.read(device=self._parent.serial)
    #     # parse the data here!!!
    #     return data

    # def subscribe(self, path):
    #     self._module.subscribe(path, device=self._parent.serial)

    # def unsubscribe(self, path):
    #     self._module.unsubscribe(path, device=self._parent.serial)

    # def save(self):
    #     self._module.save(device=self._parent.serial)
