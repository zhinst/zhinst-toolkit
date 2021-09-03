import time
import numpy as np
from typing import List, Dict

from .base import BaseInstrument
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.interface import LoggerModule

_logger = LoggerModule(__name__)


MAPPINGS = {
    "bandwidthcontrol": {0: "manual", 1: "fixed", 2: "automatic"},
    "save_fileformat": {0: "matlab", 1: "csv", 2: "zview", 3: "sxm", 4: "hdf5"},
    "scan": {0: "sequential", 1: "binary", 2: "bidirectional", 3: "reverse"},
    "xmapping": {0: "linear", 1: "logarithmic"},
    "signal_sources": {
        "demod0": "/demods/0/sample",
        "demod1": "/demods/1/sample",
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

    The Sweeper Module allows for simple and efficient parameter sweeps while
    acquiring data streams from mutiple different signal sources. The  module
    supports well defined sweeps of various parameters as well as application
    specific measurement presets. For more information on how to use the Sweeper
    Module, have a look at the LabOne Programming Manual.

    This base class is overwritten by device specific Sweeper Modules with
    additional signal sources and types. After setup, the nodetree of the module
    is retrieved from the API and added to the Sweeper object attributes as
    `zhinst-toolkit` :class:`Parameters`.

    For a list of device parameters that support sweeping, use the
    `sweep_parameter_list()` method.

        >>> mfli.sweeper.sweep_parameter_list()
        ['auxout0offset',
        'auxout1offset',
        'auxout2offset',
        'auxout3offset',
        'demdod0phase',
        'demdod1phase',
        'frequency',
        'output0amp',
        'output0offset']

    A typical measurement configuration for a simple frequency sweep would look
    like this:

        >>> mfli.sweeper.start(1e3)
        >>> mfli.sweeper.stop(510e3)
        >>> mfli.sweeper.samplecount(100)
        >>> mfli.sweeper.sweep_parameter("frequency")
        set sweep parameter to 'frequency': 'oscs/0/freq'

    Similarly to the :class:`DAQModule`, signals can be listed with
    `signals_list()` and added to the measurement with `signals_add(...)`.

        >>> mf.sweeper.signals_list()
        ['auxin0', 'demod0', 'demod1', 'imp0']
        >>> signal = mfli.sweeper.signals_add("demod0")

    The sweep is performed and the measurement result for the acquired signal is
    added as an entry in the `results` dictionary of the Sweeper Module.

        >>> mfli.sweeper.measure()
        Subscribed to: '/dev3337/demods/0/sample'
        Sweeping 'oscs/0/freq' from 1000.0 to 510000.0
        Progress: 0.0%
        Progress: 6.0%
        Progress: 12.0%
        ...
        >>> result = mfli.sweeper.results[signal]

    For more information on the results object, see the documentation for
    :class:`zhinst.toolkit.control.drivers.base.sweeper.SweeperResult` below.

    Attributes:
        signals (list): A list of node strings of signals that are added to the
            measurement and will be subscribed to before data acquisition.
        results (dict):  A dictionary with signal strings as keys and
            :class:`zhinst.toolkit.control.drivers.base.daq.SweeperResult`
            objects as values that hold all the data of the measurement result.

    """

    def __init__(self, parent: BaseInstrument, clk_rate: float = 60e6) -> None:
        self._parent = parent
        self._module = None
        self._signals = []
        self._results = {}
        self._clk_rate = clk_rate
        # the `streaming_nodes` are used as all available signal sources for the data acquisition
        self._signal_sources = self._parent._get_streamingnodes()
        self._sweep_params = {}

    def _setup(self) -> None:
        self._module = self._parent._controller.connection.sweeper_module
        # add all parameters from nodetree
        nodetree = self._module.get_nodetree("*")
        for k, v in nodetree.items():
            name = k[1:].replace("/", "_")
            mapping = MAPPINGS[name] if name in MAPPINGS.keys() else None
            setattr(self, name, Parameter(self, v, device=self, mapping=mapping))
        self._init_settings()

    def _set(self, *args, **kwargs):
        if kwargs.get("sync", False):
            _logger.warning(
                "The sweeper module does not support the `sync` flag."
            )
        if self._module is None:
            _logger.error(
                "This DAQ is not connected to a dataAcquisitionModule!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return self._module.set(*args, device=self._parent.serial)

    def _get(self, *args, valueonly: bool = True):
        if self._module is None:
            _logger.error(
                "This DAQ is not connected to a dataAcquisitionModule!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        data = self._module.get(*args, device=self._parent.serial)
        return list(data.values())[0][0] if valueonly else data

    def signals_add(self, signal_source: str) -> str:
        """Adds a signal to the measurement.

        The according signal node path will be generated and added to the
        module's `signal` list attribute. The signal node will be subscribed to
        before measurement and the :class:`SweeperResult` for this signal will
        be added as an item in the `results` attribute after measurement.
        Available signal sources can be listed using `signals_list()`.

        Arguments:
            signal_source (str): A keyword string that specifies the source of
                the signal, e.g. "demod1".

        Returns:
            The exact node string that will be subscribed to, can be used as a
            key in the results dict to get the measurement result to this signal.

        """
        signal_node = "/" + self._parent.serial
        signal_node += self._parse_signals(signal_source)
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def signals_clear(self) -> None:
        """Resets the `signal` list attribute to an empty list."""
        self._signals = []

    def signals_list(self) -> List:
        """Lists the keywords for available signals that can be added to the
        measurement.

        Returns:
            A list of the available signals.

        """
        return list(self._signal_sources.keys())

    def sweep_parameter_list(self) -> List:
        """Lists the keywords for available parameters that can be swept during
        the measurement.

        Returns:
            A list with keywords of the available sweep parameters.

        """
        return list(self._sweep_params.keys())

    def sweep_parameter(self, param: str) -> None:
        """Sets the sweep parameter.

        The parameter to sweep should be given by a keyword string. The
        available parameters can be listed with `sweep_parameter_list()`.

        Arguments:
            param (str): The string corresponding to the parameter to sweep
                during measurement.

        """
        node = self._parse_sweep_param(param)
        self._set("/gridnode", node)
        print(f"set sweep parameter to '{param}': '{node}'")

    def measure(self, verbose: bool = True, timeout: bool = 20) -> None:
        """Performs the measurement.

        Starts a measurement and stores the result in `sweeper.results`. This
        method subscribes to all the paths previously added to
        `sweeper.signals`, then starts the measurement, waits until the
        measurement is finished and eventually reads the result.

        Keyword Arguments:
            verbose (bool): A flag to enable or disable output on the console.
                (default: True)
            timeout (int): The measurement will be stopped after timeout. The
                value is given in seconds. (default: 20)

        Raises:
            TimeoutError: if the measurement is not completed before
                timeout.

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
                _logger.error(
                    f"{self.name}: Measurement timed out!",
                    _logger.ExceptionTypes.TimeoutError,
                )
        print("Finished")
        result = self._module.read(flat=True)
        self._module.finish()
        self._module.unsubscribe("*")
        self._get_result_from_dict(result)

    def application_list(self) -> List:
        """Lists the availbale application presets.

        Returns:
            A list of keywprd strings with the available applications.

        """
        return list(APPLICATIONS.keys())

    def application(self, application: str) -> None:
        """Sets one of the available application presets.

        The applications are defined in the global variable `APPLICATIONS`. They
        include `parameter_sweep`, `noise_amplitude_sweep`,
        `frequency_response_analyzer` and more.

        Arguments:
            application (str): The keyword for the application. See available
                applications with `application_list()`.

        """
        if application not in APPLICATIONS.keys():
            _logger.error(
                f"Application must be one of {list(APPLICATIONS.keys())}.",
                _logger.ExceptionTypes.ToolkitError,
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

    def _parse_signals(self, source: str) -> str:
        source = source.lower()
        if source not in self._signal_sources:
            _logger.error(
                f"Signal source must be in {self._signal_sources.keys()}",
                _logger.ExceptionTypes.ToolkitError,
            )
        return self._signal_sources[source]

    def _parse_sweep_param(self, param: str) -> str:
        if param not in self._sweep_params.keys():
            _logger.error(
                f"The parameter {param} must be one of "
                f"{list(self._sweep_params.keys())}",
                _logger.ExceptionTypes.ToolkitError,
            )
        return self._sweep_params[param]

    def _get_result_from_dict(self, result: Dict) -> None:
        self._results = {}
        for node in self.signals:
            node = node.lower()
            if node not in result.keys():
                _logger.error(
                    f"No data acquired for signal {node}",
                    _logger.ExceptionTypes.ToolkitError,
                )
            self._results[node] = SweeperResult(node, result[node][0][0])

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
    """A wrapper class around the result of a :class:`SweeperModule`
    measurement.

    Adds all the items of the dictionary returned from the API as attributes to
    the class, e.g. attributes like `value`, `grid`, etc.

    Attributes:
        attributes (list): A list of all the attributes that were returned from
            the API as a measurement result.

    """

    def __init__(self, path: str, result_dict: Dict) -> None:
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
