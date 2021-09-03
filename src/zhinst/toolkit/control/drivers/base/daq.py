import time
import numpy as np
from typing import List, Dict

from .base import BaseInstrument
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.interface import LoggerModule

_logger = LoggerModule(__name__)


MAPPINGS = {
    "edge": {1: "rising", 2: "falling", 3: "both"},
    "eventcount_mode": {0: "sample", 1: "increment"},
    "fft_window": {
        0: "rectangular",
        1: "hann",
        2: "hamming",
        3: "blackman",
        16: "exponential",
        17: "cosine",
        17: "sine",
        18: "cosine_squared",
    },
    "grid_direction": {0: "forward", 1: "reverse", 2: "bidirectional"},
    "grid_mode": {1: "nearest", 2: "linear", 4: "exact"},
    "save_fileformat": {0: "matlab", 1: "csv", 2: "zview", 3: "sxm", 4: "hdf5"},
    "type": {
        0: "continuous",
        1: "edge",
        2: "dio",
        3: "pulse",
        4: "tracking",
        5: "change",
        6: "hardware",
        7: "tracking_pulse",
        8: "eventcount",
    },
}


class DAQModule:
    """Implements a :class:`Data Acquisition Module` for Lock-In instruments.

    The data acquisition module is a powerful tool that builds on top of LabOne.
    It allows for triggered acquisition of multiple data streams on an
    equidistant temporal grid. For more information on how to use the DAQ
    Module, have a look at the LabOne Programming Manual.

    This base class is overwritten by device specific DAQ classes with
    additional signal sources and types. After setup, the nodetree of the module
    is retrieved from the API and added to the DAQModule object attributes as
    `zhinst-toolkit` :class:`Parameters`.

    In a typical measurement using the DAQ Module one would first configure its
    trigger and grid settings.

        >>> # configure a measurement
        >>> mfli.daq.fft_window("rectangular")
        >>> mfli.daq.type("continuous")
        >>> mfli.daq.grid_cols(512)
        >>> mfli.daq.grid_rows(10)

    The signal streams that are available for acquisition can be listed using
    `signals_list(...)`.

        >>> # list available signal sources ...
        >>> mf.daq.signals_list()
        ['auxin0', 'demod0', 'demod1', 'imp0']
        >>> # ... and according singal types
        >>> mf.daq.signals_list("demod1")
        ['x', 'y', 'r', 'xiy', 'theta', 'frequency', 'auxin0', 'auxin1', 'dio']

    To specify which signals should be acquired during the measurement, they
    need to be added to the measurement. This is done with the
    `signals_add(...)` method. Note that the return value is a string with the
    exact node path that will be subscribed to during the measurement. The
    string can be used later as a key in the `results` dictionary.

        >>> # add signals to the measurement
        >>> mf.daq.signals_clear()
        >>> signal1 = mf.daq.signals_add("demod1", "r")     # specify signal_source and signal_type
        >>> signal2 = mf.daq.signals_add("demod1", "theta")
        >>> signal3 = mf.daq.signals_add("demod1", "xiy", fft=True)

    The measurement is started ...

        >>> # start the measurement
        >>> mf.daq.measure()
        subscribed to: /dev3337/demods/0/sample.r.avg
        subscribed to: /dev3337/demods/0/sample.theta.avg
        subscribed to: /dev3337/demods/0/sample.xiy.fft.abs.avg
        Progress: 0.0%
        Progress: 40.0%
        ...

    ... and afterwards the results can be found in the `results` attribute of
    the :class:`DAQModule`. The values in the dictionary are of type
    :class:`DAQResults`.

        >>> # retrieve the measurement results
        >>> result1 = mf.daq.results[signal1]
        >>> result2 = mf.daq.results[signal2]
        >>> result3 = mf.daq.results[signal3]
        >>> ...
        >>> result1
        <zhinst.toolkit.control.drivers.base.daq.DAQResult object at 0x0000023B8467D588>
            path:        /dev3337/demods/0/sample.xiy.fft.abs.avg
            value:       (10, 511)
            frequency:   (511,)

    See below for details on
    :class:`zhinst.toolkit.control.drivers.base.daq.DAQResult`.

    Attributes:
        signals (list): A list of node strings of signals that are added to the
            measurement and will be subscribed to before data acquisition.
        results (dict): A dictionary with signal strings as keys and
            :class:`zhinst.toolkit.control.drivers.base.daq.DAQResult` objects
            as values that hold all the data of the measurement result.

    """

    def __init__(self, parent: BaseInstrument, clk_rate: float = 60e6) -> None:
        self._parent = parent
        self._module = None
        self._signals = []
        self._results = {}
        self._clk_rate = clk_rate
        # the `streaming_nodes` are used as all available signal sources for the data acquisition
        self._signal_sources = self._parent._get_streamingnodes()
        self._signal_types = {
            "auxin": {"auxin1": ".Auxin0", "auxin2": ".Auxin1"},
            "demod": {
                "x": ".X",
                "y": ".Y",
                "r": ".R",
                "xiy": ".xiy",
                "theta": ".Theta",
                "frequency": ".Frequency",
                "auxin0": ".AuxIn0",
                "auxin1": ".AuxIn1",
                "dio": ".Dio",
            },
            "imp": {
                "real": ".RealZ",
                "imag": ".ImagZ",
                "abs": ".AbsZ",
                "phase": ".PhaseZ",
                "frequency": ".Frequency",
                "param0": ".Param0",
                "param1": ".Param1",
            },
            "cnt": {"": ".Value"},
            "pid": {"": ""},
        }
        self._trigger_signals = {}
        self._trigger_types = {}

    def _setup(self) -> None:
        self._module = self._parent._controller.connection.daq_module
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
                "The daq module does not support the `sync` flag."
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

    def _init_settings(self):
        self._set("preview", 1)
        self._set("historylength", 10)
        self._set("bandwidth", 0)
        self._set("hysteresis", 0.01)
        self._set("level", 0.1)
        self._set("clearhistory", 1)
        self._set("bandwidth", 0)

    def trigger_list(self, source=None) -> List:
        """Returns a list of all the available signal sources for triggering.

        Keyword Arguments:
            source (str): specifies the signal source to return signal types
                (default: None)

        Returns:
            Returns all available trigger sources by default. If the keyword is
            specified with one of the trigger sources, all the available trigger
            types for the trigger source are returned.

        """
        sources = list(self._trigger_signals.keys())
        if source is None:
            return sources
        else:
            for signal in self._trigger_types.keys():
                if signal in source:
                    return list(self._trigger_types[signal].keys())

    def trigger(self, trigger_source: str, trigger_type: str) -> None:
        """Sets the trigger signal of the *DAQ Module*.

        This method can be used to specify the signal used to trigger the data
        acquisition. Use the method `trigger_list()` to see the available
        trigger signal sources and types.The trigger node can also be set
        directly using the module Parameter `triggernode`.

        Arguments:
            trigger_source (str): A string that specifies the source of the
                trigger signal, e.g. "demod0".
            trigger_trype (str): A string that specifies the type of the
                trigger signal, e.g. "trigin1".

        """
        trigger_node = self._parse_trigger(trigger_source, trigger_type)
        self._set("/triggernode", trigger_node)
        print(f"set trigger node to '{trigger_node}'")

    def signals_list(self, source=None) -> List:
        """Returns a list of all the available signal sources for data acquisition.

        Keyword Arguments:
            source (str): specifies the signal source to return signal types
                (default: None)

        Returns:
            Returns all available signal sources by default. If the keyword is
            specified with one of the signal sources, all the available signal
            types for the signal source are returned.

        """
        sources = list(self._signal_sources.keys())
        if source is None:
            return sources
        else:
            for signal in self._signal_types.keys():
                if signal in source:
                    return list(self._signal_types[signal].keys())
            else:
                return sources

    def signals_add(
        self,
        signal_source: str,
        signal_type: str = "",
        operation: str = "avg",
        fft: bool = False,
        complex_selector: str = "abs",
    ) -> str:
        """Add a signal to the signals list to be subscribed to during measurement.

        The specified signal is added to the property *signals* list. On
        `measure()`, the *DAQ Module* subscribes to all the signal nodes in the
        list.

        Arguments:
            signal_source (str): The source of the signal, e.g. 'demod0'. See
                `signals_list()` for available signals.

        Keyword Arguments:
            signal_type (str): The type of the signal. Depends on the given
                source, e.g. for demod signals the types'X', 'Y', 'R', 'Theta',
                ... are available. See `signals_list({signal source})` for
                available signal types. (default: "")
            operation (str): The operation that is performed on the acquired
                signal, e.g. the average of data points ('avg'), the standard
                deviation of the signal ('std') or single points ('replace').
                (default: "avg")
            fft (bool): A flag to enable the fourier transform (FFT) of the
                acquired signal.  (default: False)
            complex_selector (str):  If the FFT is enabled, this selects the
                complex value of the result, e.g. 'abs', 'phase', 'real',
                'imag'. (default: "abs")

        Returns:
            A string with the exact signal node that will be acquired during the
            measurement. It can be used as a key in the `results` dict to
            retrieve the measurement result corresponding to this signal, e.g.

                >>> signal = mfli.daq.signal_add("demod0", "r")
                /dev3337/demods/0/sample.r.avg
                >>> mfli.daq.measure()
                >>> ...
                >>> result = mfli.daq.results[signal]

        """
        signal_node = self._parse_signals(
            signal_source, signal_type, operation, fft, complex_selector
        )
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def signals_clear(self) -> None:
        """Resets the signals list."""
        self._signals = []

    def measure(self, verbose: bool = True, timeout: float = 20) -> None:
        """Performs the measurement.

        Starts a measurement and stores the result in `daq.results`. This
        method subscribes to all the paths previously added to `daq.signals`,
        then starts the measurement, waits until the measurement in finished
        and eventually reads the result.

        Keyword Arguments:
            verbose (bool): A flag to enable or disable console output during
                the measurement. (default: True)
            timeout (int): The measurement will be stopped after the timeout.
                The value is given in seconds. (default: 20)

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
        if verbose:
            print("Finished")
        result = self._module.read(flat=True)
        self._module.finish()
        self._module.unsubscribe("*")
        self._get_result_from_dict(result)

    def _parse_signals(
        self,
        signal_source: str,
        signal_type: str,
        operation: str,
        fft: bool,
        complex_selector: str,
    ) -> str:
        signal_node = "/" + self._parent.serial
        signal_node += self._parse_signal_source(signal_source)
        signal_node += self._parse_signal_type(signal_type, signal_source)
        signal_node += self._parse_fft(fft, complex_selector)
        signal_node += self._parse_operation(operation)
        return signal_node.lower()

    def _parse_signal_source(self, source: str) -> str:
        source = source.lower()
        if source not in self._signal_sources:
            _logger.error(
                f"Signal source must be in {self._signal_sources.keys()}",
                _logger.ExceptionTypes.ToolkitError,
            )
        return self._signal_sources[source]

    def _parse_signal_type(self, signal_type: str, signal_source: str) -> str:
        signal_source = signal_source.lower()
        signal_type = signal_type.lower()
        types = {}
        for signal in self._signal_types.keys():
            if signal in signal_source:
                types = self._signal_types[signal]
        if signal_type not in types.keys():
            _logger.error(
                f"Signal type must be in {types.keys()}",
                _logger.ExceptionTypes.ToolkitError,
            )
        return types[signal_type]

    def _parse_operation(self, operation: str) -> str:
        operations = ["replace", "avg", "std"]
        if operation not in operations:
            _logger.error(
                f"Operation must be in {operations}",
                _logger.ExceptionTypes.ToolkitError,
            )
        if operation == "replace":
            operation = ""
        return f".{operation}"

    def _parse_fft(self, fft: bool, selector: str) -> str:
        if fft:
            selectors = ["real", "imag", "abs", "phase"]
            if selector not in selectors:
                _logger.error(
                    f"Operation must be in {selectors}",
                    _logger.ExceptionTypes.ToolkitError,
                )
            return f".fft.{selector}"
        else:
            return ""

    def _parse_trigger(self, trigger_source: str, trigger_type: str) -> str:
        trigger_node = "/" + self._parent.serial
        trigger_node += self._parse_trigger_source(trigger_source)
        trigger_node += self._parse_trigger_type(trigger_source, trigger_type)
        return trigger_node

    def _parse_trigger_source(self, source: str) -> str:
        source = source.lower()
        sources = self._trigger_signals
        if source not in sources:
            _logger.error(
                f"Signal source must be in {sources.keys()}",
                _logger.ExceptionTypes.ToolkitError,
            )
        return sources[source]

    def _parse_trigger_type(self, trigger_source: str, trigger_type: str) -> str:
        trigger_source = trigger_source.lower()
        trigger_type = trigger_type.lower()
        types = {}
        for signal in self._trigger_types.keys():
            if signal in trigger_source:
                types = self._trigger_types[signal]
        if trigger_type.lower() not in types.keys():
            _logger.error(
                f"Signal type must be in {types.keys()}",
                _logger.ExceptionTypes.ToolkitError,
            )
        return types[trigger_type]

    def _get_result_from_dict(self, result: Dict):
        self._results = {}
        for node in self.signals:
            node = node.lower()
            if node not in result.keys():
                _logger.error(
                    f"The signal {node} is not in {list(result.keys())}",
                    _logger.ExceptionTypes.ToolkitError,
                )
            self._results[node] = DAQResult(
                node, result[node][0], clk_rate=self._clk_rate
            )

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

    @property
    def signals(self):
        return self._signals

    @property
    def results(self):
        return self._results


class DAQResult:
    """A wrapper class around the result of a DAQ Module measurement.

    The Data Acquisition Result class holds all measurement information returned
    from the API. The attribute `value` is a two-dimensional numpy array with
    the measured data along the measured grid. Depending on whether the time
    trace or the FFT of a signal was acquired, either the `time` of `frequency`
    attribute holds a 1D numpy array with the correct axis values calculated
    from the measurement grid.

        >>> signal = mf.daq.signals_add("demod1", "r")
        >>> mf.daq.measure()
        ...
        >>> result = mf.daq.results[signal]
        >>> result
        <zhinst.toolkit.control.drivers.base.daq.DAQResult object at 0x0000023B8467D588>
            path:        /dev3337/demods/0/sample.r.avg
            value:       (10, 511)
            time:        (511,)
        >>> result.header
           {'systemtime': array([1585136936490779], dtype=uint64),
            'createdtimestamp': array([548560038356], dtype=uint64),
            'changedtimestamp': array([548669852116], dtype=uint64),
            'flags': array([1977], dtype=uint32),
            ...
        >>> plt.imshow(result.value, extent=[result.time[0], result.time[-1], 0, result.shape[0]])

    Attributes:
        value (array): A 2D numpy array with the measurement result.
        shape (tuple): A tuple with the shape of the acquired data which
            corresponds to the according grid settings.
        time (array): A 1D numpy array containing the time axis of the
            measurement in seconds. Calculated from the returned timestamps
            using the DAC clock rate. If the result is a Fourier transform this
            value is `None`.
        frequency (array): A 1D numpy array with the frequency values for FFT
            measurements in Hertz. If the signal is not a FFT this value is
            `None` The frequency grid is calculated from the grid settings. If
            the "xiy" complex signal of the demodulator data stream is acquired,
            the frequency spectrum is symmetric around 0 Hz, otherwise it is
            positive.
        header (dict): A dictionary containing all information about the
            measurement settings.

    """

    def __init__(self, path: str, result_dict: Dict, clk_rate: float = 60e6) -> None:
        self._path = path
        self._clk_rate = clk_rate
        self._is_fft = "fft" in self._path
        self._result_dict = result_dict
        self._header = self._result_dict.get("header", {})
        self._value = self._result_dict.get("value")
        self._time = None
        self._frequencies = None
        if not self._is_fft:
            self._time = self._claculate_time()
        else:
            self._frequency = self._calculate_freqs()

    @property
    def value(self):
        return self._value

    @property
    def header(self):
        return self._header

    @property
    def time(self):
        return self._time

    @property
    def frequency(self):
        return self._frequency

    @property
    def shape(self):
        return self._value.shape

    def _claculate_time(self):
        timestamp = self._result_dict["timestamp"]
        return (timestamp[0] - timestamp[0][0]) / self._clk_rate

    def _calculate_freqs(self):
        bin_count = len(self.value[0])
        bin_resolution = self.header["gridcoldelta"]
        frequencies = np.arange(bin_count)
        bandwidth = bin_resolution * len(frequencies)
        frequencies = frequencies * bin_resolution
        if "xiy" in self._path:
            frequencies = frequencies - bandwidth / 2.0 + bin_resolution / 2.0
        return frequencies

    def __repr__(self):
        s = super().__repr__()
        s += "\n\n"
        s += f"path:        {self._path}\n"
        s += f"value:       {self._value.shape}\n"
        if self._is_fft:
            s += f"frequency:   {self._frequency.shape}\n"
        else:
            s += f"time:        {self._time.shape}\n"
        return s
