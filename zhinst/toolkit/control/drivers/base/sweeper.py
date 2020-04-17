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
    """Implements a base Sweeper Module for Lock-In instruments. 
    
    This base class is overwritten by device specific Sweeper classes with 
    additional signal sources and types. After setup, the nodetree of the module 
    is retrieved from the API and added to the Sweeper object attributes as 
    zhinst-toolkit Parameters.

    Attributes:
        signals (list): list of node strings of signals added to the measurement
        results (dict): dict with signals as keys and values :class:`zhinst.toolkit.control.drivers.base.sweeper.SweeperResult` 
    
    """

    def __init__(self, parent, clk_rate=60e6):
        self._parent = parent
        self._module = None
        self._signals = []
        self._results = {}
        self._clk_rate = clk_rate
        # the `streaming_nodes` are used as all available signal sources for the data acquisition
        self._signal_sources = self._parent._get_streamingnodes()
        self._sweep_params = {}

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

    def signals_add(self, signal_source):
        """Adds a signal to the measurement.
        
        The according signal node path will be generated and added to the 
        module's signal list. The signal node will be subscribed to before 
        measurement. Available signal sources can be listed using 
        `signals_list()`.
        
        Arguments:
            signal_source (str): specifies the source of the signal, e.g. 
                "demod1"
        
        Returns:
            The exact node string that will be subscribed to, can be used as a 
            key in the results dict to get the measurement result to this signal.

        """
        signal_node = "/" + self._parent.serial
        signal_node += self._parse_signals(signal_source)
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def signals_clear(self):
        """Resets the signal list."""
        self._signals = []

    def signals_list(self):
        """Lists the available signals that can be added to the measurement.
        
        Returns:
            (list) a list of the available signals

        """
        return list(self._signal_sources.keys())

    def sweep_parameter_list(self):
        """Lists the available parameters that can be swept during the measurement.
        
        Returns:
            (list) a list of the available available sweep parameters

        """
        return list(self._sweep_params.keys())

    def sweep_parameter(self, param):
        """Sets the sweep parameter. 
        
        The available parameters can be listed with `sweep_parameter_list()`.
        
        Arguments:
            param (str)

        """
        node = self._parse_sweep_param(param)
        self._set("/gridnode", node)
        print(f"set sweep parameter to '{param}': '{node}'")

    def measure(self, verbose=True, timeout=20):
        """Performs the measurement.
        
        Keyword Arguments:
            verbose (bool): flag to enable output (default: True)
            timeout (int): measurement stopped after timeout, in seconds 
                (default: 20)
     
        """
        self._set("endless", 0)
        self._set("clearhistory", 1)
        for path in self.signals:
            self._module.subscribe(path)
            if verbose:
                print(f"subscribed to: {path}")
        if verbose:
            print(
                f"Sweeping {self._get('/gridnode')} from {self._get('/start')} to {self._get('/stop')}"
            )
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
        """Lists the availbale application presets.
        
        Returns:
            A list of strings with the available applications.
        
        """
        return list(APPLICATIONS.keys())

    def application(self, application):
        """Sets one of the available application rpesets. 
        
        The applications are defined in the global variable APPLICATIONS.
        
        Arguments:
            application (str)
        
        """
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

    def _parse_signals(self, source):
        source = source.lower()
        if source not in self._signal_sources:
            raise ZHTKException(
                f"Signal source must be in {self._signal_sources.keys()}"
            )
        return self._signal_sources[source]

    def _parse_sweep_param(self, param):
        if param not in self._sweep_params.keys():
            raise ZHTKException(
                f"The parameter {param} must be one of {list(self._sweep_params.keys())}"
            )
        return self._sweep_params[param]

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
            ("historylength", 100),
            ("settling/inaccuracy", 0.0001),
            ("averaging/sample", 1),
            ("bandwidth", 1000),
            ("maxbandwidth", 1250000),
            ("omegasuppression", 40),
            ("order", 4),
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
    """A wrapper class around the result of a Sweeper module measurement. Adds all 
    
    the items of the dictionary returned from the API as attributes of the 
    class, e.g. value, grid etc.

    """

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
