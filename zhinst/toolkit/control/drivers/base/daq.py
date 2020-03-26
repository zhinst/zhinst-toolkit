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
        7: "tracking_pulse",
        8: "eventcount",
    },
}


class DAQModule:
    def __init__(self, parent, clk_rate=60e6):
        self._parent = parent
        self._module = None
        self._signals = []
        self._results = {}
        self._clk_rate = clk_rate

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

    def trigger(self, trigger_source, trigger_type):
        trigger_node = self._parse_trigger(trigger_source, trigger_type)
        self._set("/triggernode", trigger_node)
        print(f"set trigger node to '{trigger_node}'")

    def signals_add(
        self,
        signal_source,
        signal_type="",
        operation="avg",
        fft=False,
        complex_selector="abs",
    ):
        signal_node = self._parse_signals(
            signal_source, signal_type, operation, fft, complex_selector
        )
        if signal_node not in self.signals:
            self._signals.append(signal_node)
        return signal_node

    def signals_clear(self):
        self._signals = []

    def measure(self, verbose=True, timeout=20):
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
        print("Finished")
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

    def _parse_signals(
        self, signal_source, signal_type, operation, fft, complex_selector,
    ):
        raise NotImplementedError()

    def _parse_trigger(self, trigger_source, trigger_type):
        raise NotImplementedError()

    def _get_result_from_dict(self, result):
        self._results = {}
        for node in self.signals:
            node = node.lower()
            print(f"getting result from: {node}")
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


class DAQResult:
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
            self._frequencies = self._calculate_freqs()

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
    def frequencies(self):
        return self._frequencies

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
        s += f"shape:       {self.shape}\n"
        s += f"value:       {self._value}\n"
        if self._is_fft:
            s += f"frequencies: {self._frequencies}\n"
        else:
            s += f"time:        {self._time}\n"
        return s
