import time
import numpy as np

from .base import ZHTKException
from control.nodetree import Parameter


MAPPINGS = {
    "bandwidthcontrol": {0: "manual", 1: "fixed", 2: "automatic",},
    "save_fileformat": {0: "matlab", 1: "csv", 2: "zview", 3: "sxm", 4: "hdf5",},
    "scan": {0: "sequential", 1: "binary", 2: "bidirectional", 3: "reverse"},
    "xmapping": {0: "linear", 1: "logarithmic",},
    "signal_sources": {
        "demod1": "/demods/0/sample",
        "demod2": "/demods/1/sample",
        "imp": "/demods/1/sample",
    },
}


class SweeperModule:
    def __init__(self, parent):
        self._parent = parent
        self._module = None
        self._signals = []
        self._results = {}
        self._clk_rate = 60e6

    def _setup(self):
        self._module = self._parent._controller._connection.sweeper_module
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
        self._set("device", "dev3337")
        self._set("historylength", 100)
        self._set("settling/inaccuracy", 0.0001)
        self._set("averaging/sample", 1)
        self._set("bandwidth", 1000)
        self._set("maxbandwidth", 1250000)
        self._set("omegasuppression", 40)
        self._set("order", 4)
        self._set("gridnode", "/dev3337/oscs/0/freq")
        self._set("save/directory", "/data/LabOne/WebServer")
        self._set("averaging/tc", 0)
        self._set("averaging/time", 0)
        self._set("bandwidth", 1000)
        self._set("start", 1000)
        self._set("stop", 1000000)
        self._set("omegasuppression", 40)
        self._set("order", 4)
        self._set("settling/inaccuracy", 0.0001)
        self._set("stop", 1000000)
        self._set("start", 1000)
        self._set("stop", 510000)
        self._set("endless", 0)

    def signals_add(self, signal_source):
        sources = MAPPINGS["signal_sources"]
        if signal_source.lower() not in sources.keys():
            raise ZHTKException(f"Signal source must be in {sources.keys()}")
        signal_node = "/"
        signal_node += self._parent.serial
        signal_node += f"{sources[signal_source]}"
        signal_node = signal_node.lower()
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def signals_clear(self):
        self._signals = []

    def signals_list(self):
        return list(MAPPINGS["signal_sources"].keys())

    def measure(self, single=True, verbose=True, timeout=20):
        self._set("endless", int(not single))
        self._set("clearhistory", 1)
        for path in self.signals:
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
        print("Finished")
        result = self._module.read(flat=True)
        self._module.finish()
        self._module.unsubscribe("*")
        return self._get_result_from_dict(result)

    @property
    def signals(self):
        return self._signals

    @property
    def results(self):
        return self._results

    def _get_result_from_dict(self, result):
        self._results = {}
        for node in self.signals:
            node = node.lower()
            if node not in result.keys():
                raise ZHTKException()
            result = SweeperResult(node, result[node][0][0])
            self._results[node] = result
        return result

    def __repr__(self):
        s = super().__repr__()
        s += "\n\nsignals:\n"
        for signal in self.signals:
            s += f" - '{signal}'\n"
        s += "parameters:\n"
        for key, value in self.__dict__.items():
            if isinstance(value, Parameter):
                s += f" - {key}\n"
        return s


class SweeperResult:
    def __init__(self, path, result_dict):
        self._path = path
        self._result_dict = result_dict
        for k, v in result_dict.items():
            setattr(self, k, v)

    @property
    def attributes(self):
        attributes = []
        for k in self.__dict__.keys():
            if not k.startswith("_"):
                attributes.append(k)
        return attributes

    def __repr__(self):
        s = super().__repr__()
        s += "\n\nattributes:\n"
        for a in self.attributes:
            s += f" - {a}\n"
        return s
