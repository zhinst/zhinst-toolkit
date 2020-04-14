import time
import numpy as np

from .base import ZHTKException
from zhinst.toolkit.control.nodetree import Parameter


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
        18: "cosine_squared",
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
        7: "tracking_pulse",
        8: "eventcount",
    },
}


class DAQModule:
    """Implements a base Data Acquisition Module for Lock-In instruments. 
    
    This base class is overwritten by device specific DAQ classes with 
    additional signal sources and types. After setup, the nodetree of the module 
    is retrieved from the API and added to the Sweeper object attributes as 
    zhinst-toolkit Parameters.

    Properties:
        signals (list)
        results (list)
    
    """

    def __init__(self, parent, clk_rate=60e6):
        self._parent = parent
        self._module = None
        self._signals = []
        self._results = {}
        self._clk_rate = clk_rate
        # the `streaming_nodes` are used as all available signal sources for the data acquisition
        self._signal_sources = self._parent._get_streamingnodes()
        self._signal_types = {
            "auxin": {"auxin1": ".Auxin0", "auxin2": ".Auxin1",},
            "demod": {
                "x": ".X",
                "y": ".Y",
                "r": ".R",
                "xiy": ".xiy",
                "theta": ".Theta",
                "frequency": ".Frequency",
                "auxin1": ".AuxIn0",
                "auxin2": ".AuxIn1",
                "dio": ".Dio",
            },
            "imp": {
                "real": ".RealZ",
                "imag": ".ImagZ",
                "abs": ".AbsZ",
                "theta": ".PhaseZ",
                "frequency": ".Frequency",
                "param1": ".Param0",
                "param2": ".Param1",
            },
            "cnt": {"": ".Value"},
        }
        self._trigger_signals = {}
        self._trigger_types = {}

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

    def trigger_list(self, source=None):
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
            else:
                return sources

    def trigger(self, trigger_source, trigger_type):
        """Sets the trigger signal by specifying the signal source and type.
        
        The trigger node can also be set directly using the module Parameter 
        'triggernode'.
        
        """
        trigger_node = self._parse_trigger(trigger_source, trigger_type)
        self._set("/triggernode", trigger_node)
        print(f"set trigger node to '{trigger_node}'")

    def signals_list(self, source=None):
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
        signal_source,
        signal_type="",
        operation="avg",
        fft=False,
        complex_selector="abs",
    ):
        """Add a signal to the signals list to be subscribed to during measurement.
        
        Arguments:
            signal_source (str): source of the signal, e.g. 'demod1'
        
        Keyword Arguments:
            signal_type (str): type of the signal, depends on the source, e.g. 
                'X', 'Y', 'R', 'Theta' ... (default: "")
            operation (str): operation performed on the acquired signal, e.g. 
                averaging ('avg'), standard deviation ('std') or single points 
                ('replace') (default: "avg")
            fft (bool): flag to enable the fourier transform of the signal 
                (default: False)
            complex_selector (str):  if the FFT is enabled, this selects the 
                complex value of the result, e.g. 'abs', 'phase', 'real', 'imag' 
                (default: "abs")
        
        Returns:
            A string with the exact node that will be subscribed to. Can be used 
            as a key in the 'results' dict to retrieve the measurement result 
            corresponding to this signal 
        
        """
        signal_node = self._parse_signals(
            signal_source, signal_type, operation, fft, complex_selector
        )
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def signals_clear(self):
        """Resets the signals list."""
        self._signals = []

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
        self._module.execute()
        tik = time.time()
        while not self._module.finished():
            if verbose:
                print(f"Progress: {(self._module.progress()[0] * 100):.1f}%")
            time.sleep(0.5)
            tok = time.time()
            if tok - tik > timeout:
                raise TimeoutError()
        if verbose:
            print("Finished")
        result = self._module.read(flat=True)
        self._module.finish()
        self._module.unsubscribe("*")
        self._get_result_from_dict(result)

    def _parse_signals(
        self, signal_source, signal_type, operation, fft, complex_selector,
    ):
        signal_node = "/" + self._parent.serial
        signal_node += self._parse_signal_source(signal_source)
        signal_node += self._parse_signal_type(signal_type, signal_source)
        signal_node += self._parse_fft(fft, complex_selector)
        signal_node += self._parse_operation(operation)
        return signal_node.lower()

    def _parse_signal_source(self, source):
        source = source.lower()
        if source not in self._signal_sources:
            raise ZHTKException(
                f"Signal source must be in {self._signal_sources.keys()}"
            )
        return self._signal_sources[source]

    def _parse_signal_type(self, signal_type, signal_source):
        signal_source = signal_source.lower()
        signal_type = signal_type.lower()
        for signal in self._signal_types.keys():
            if signal in signal_source:
                types = self._signal_types[signal]
        if signal_type not in types.keys():
            raise ZHTKException(f"Signal type must be in {types.keys()}")
        return types[signal_type]

    def _parse_operation(self, operation):
        operations = ["replace", "avg", "std"]
        if operation not in operations:
            raise ZHTKException(f"Operation must be in {operations}")
        if operation == "replace":
            operation = ""
        return f".{operation}"

    def _parse_fft(self, fft, selector):
        if fft:
            selectors = ["real", "imag", "abs", "phase"]
            if selector not in selectors:
                raise ZHTKException(f"Operation must be in {selectors}")
            return f".fft.{selector}"
        else:
            return ""

    def _parse_trigger(self, trigger_source, trigger_type):
        trigger_node = "/" + self._parent.serial
        trigger_node += self._parse_trigger_source(trigger_source)
        trigger_node += self._parse_trigger_type(trigger_source, trigger_type)
        return trigger_node

    def _parse_trigger_source(self, source):
        source = source.lower()
        sources = self._trigger_signals
        if source not in sources:
            raise ZHTKException(f"Signal source must be in {sources.keys()}")
        return sources[source]

    def _parse_trigger_type(self, trigger_source, trigger_type):
        trigger_source = trigger_source.lower()
        trigger_type = trigger_type.lower()
        for signal in self._trigger_types.keys():
            if signal in trigger_source:
                types = self._trigger_types[signal]
        if trigger_type.lower() not in types.keys():
            raise ZHTKException(f"Signal type must be in {types.keys()}")
        return types[trigger_type]

    def _get_result_from_dict(self, result):
        self._results = {}
        for node in self.signals:
            node = node.lower()
            if node not in result.keys():
                raise ZHTKException()
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
    """A wrapper class around the result if a DAQ module measurement.
    
    Properties:
        value (array)
        header (dict)
        time (array)
        frequency (array)
        shape (tuple)

    """

    def __init__(self, path, result_dict, clk_rate=60e6):
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
