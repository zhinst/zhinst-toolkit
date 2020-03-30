import time
import numpy as np

from .base import ZHTKException
from zhinst.toolkit.control.nodetree import Parameter


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

APPLICATIONS = {
    "parameter_sweep": [
        ("settling/time", 0),
        ("averaging/sample", 1),
        ("averaging/tc", 0),
        ("averaging/time", 0),
        ("bandwidth", 1000),
        ("maxbandwidth", 1250000),
        ("bandwidthoverlap", 0),
        ("order", 4),
    ],
    "parameter_sweep_avg": [
        ("averaging/sample", 20),
        ("averaging/tc", 15),
        ("averaging/time", 0.02),
    ],
    "noise_amplitude_sweep": [
        ("settling/inaccuracy", 1e-07),
        ("averaging/sample", 1000),
        ("averaging/tc", 50),
        ("averaging/time", 0.1),
        ("bandwidth", 10),
        ("omegasuppression", 60),
    ],
    "frequency_response_analyzer": [
        ("settling/time", 0.01),
        ("settling/inaccuracy", 0.0001),
        ("averaging/sample", 20),
        ("averaging/tc", 15),
        ("averaging/time", 0.02),
        ("bandwidth", 100),
        ("maxbandwidth", 100),
        ("bandwidthoverlap", 1),
        ("omegasuppression", 40),
        ("order", 8),
    ],
    "3-omega_sweep": [
        ("averaging/sample", 20),
        ("averaging/tc", 15),
        ("averaging/time", 0.02),
        ("bandwidth", 100),
        ("omegasuppression", 100),
        ("order", 8),
    ],
    "fra_sinc_filter": [
        ("settling/time", 0.01),
        ("averaging/tc", 0),
        ("maxbandwidth", 100),
        ("bandwidthoverlap", 1),
        ("omegasuppression", 40),
        ("sincfilter", 1),
    ],
    "impedance": [
        ("settling/time", 0),
        ("settling/inaccuracy", 0.01),
        ("averaging/tc", 15),
        ("averaging/time", 0.1),
        ("bandwidth", 10),
        ("omegasuppression", 80),
        ("sincfilter", 0),
    ],
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

    def signals_add(self, signal_source, **kwargs):
        signal_node = self._parse_signals(signal_source, **kwargs)
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def _parse_signals(self, signal_source, **kwargs):
        raise NotImplementedError()

    def signals_clear(self):
        self._signals = []

    def signals_list(self):
        return list(MAPPINGS["signal_sources"].keys())

    def sweep_parameter(self, param):
        node = self._parse_sweep_param(param)
        self._set("/gridnode", node)
        print(f"set sweep parameter to '{param}': '{node}'")

    def measure(self, verbose=True, timeout=20):
        self._set("endless", 0)
        self._set("clearhistory", 1)
        for path in self.signals:
            self._module.subscribe(path)
            if verbose:
                print(f"subscribed to: {path}")
        if verbose:
            print(f"Sweeping '{self.gridnode()}' from {self.start()} to {self.stop()}")
        self._module.execute()
        tik = time.time()
        while not self._module.finished():
            if verbose:
                print(f"Progress: {(self._module.progress()[0] * 100):.1f}%")
            time.sleep(0.5)
            tok = time.time()
            if tok - tik > timeout:
                raise TimeoutError()
        print("Finished")
        result = self._module.read(flat=True)
        self._module.finish()
        self._module.unsubscribe("*")
        return self._get_result_from_dict(result)

    def application_list(self):
        return list(APPLICATIONS.keys())

    def application(self, application):
        if application not in APPLICATIONS.keys():
            raise ZHTKException(
                f"Application must be one of {list(APPLICATIONS.keys())}."
            )
        settings = APPLICATIONS[application]
        self._set(settings)
        for setting, value in settings:
            print(f"setting '{setting}' to {value}")

    @property
    def signals(self):
        return self._signals

    @property
    def results(self):
        return self._results

    def _parse_sweep_param(self, param):
        raise NotImplementedError()

    def _get_result_from_dict(self, result):
        self._results = {}
        for node in self.signals:
            node = node.lower()
            if node not in result.keys():
                raise ZHTKException()
            result = SweeperResult(node, result[node][0][0])
            self._results[node] = result
        return result

    def _init_settings(self):
        settings = [
            ("device", "dev3337"),
            ("historylength", 100),
            ("settling/inaccuracy", 0.0001),
            ("averaging/sample", 1),
            ("bandwidth", 1000),
            ("maxbandwidth", 1250000),
            ("omegasuppression", 40),
            ("order", 4),
            ("gridnode", "/dev3337/oscs/0/freq"),
            ("save/directory", "/data/LabOne/WebServer"),
            ("averaging/tc", 0),
            ("averaging/time", 0),
            ("bandwidth", 1000),
            ("start", 1000),
            ("stop", 1000000),
            ("omegasuppression", 40),
            ("order", 4),
            ("settling/inaccuracy", 0.0001),
            ("stop", 1000000),
            ("start", 1000),
            ("stop", 510000),
            ("endless", 0),
        ]
        self._set(settings)

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
