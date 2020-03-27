# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.drivers.base import (
    BaseInstrument,
    DAQModule as DAQ,
    SweeperModule as Sweeper,
    ZHTKException,
)
from zhinst.toolkit.control.drivers.uhfqa import AWG
from zhinst.toolkit.interface import DeviceTypes


class UHFLI(BaseInstrument):
    """
    High-level controller for UHFLI. Inherits from BaseInstrument and overrides 
    the _init-settings(...) method. The property awg_connection accesses the 
    connection's awg module and is used in the AWG core as 
    awg._parent._awg_module. 
    
    Reuses the device specific AWG from the UHFQA. Might want to define a 
    device-specific AWG for the UHFLI isntead.

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.UHFLI, serial, **kwargs)

    def connect_device(self, nodetree=True):
        super().connect_device(nodetree=nodetree)
        if "AWG" in self._options:
            self._awg = AWG(self, 0)
            self._awg._setup()
        self._daq = DAQModule(self, clk_rate=1.8e9)
        self._daq._setup()
        self._sweeper = SweeperModule(self)
        self._sweeper._setup()

    def _init_settings(self):
        pass
        # settings = [
        #     ("awgs/0/single", 1),
        # ]
        # self._set(settings)

    @property
    def awg(self):
        if "AWG" not in self._options:
            raise ZHTKException("The AWG option is not installed.")
        return self._awg

    @property
    def daq(self):
        return self._daq

    @property
    def sweeper(self):
        return self._sweeper


MAPPINGS = {
    "signal_sources": {
        "demod1": "/demods/0/sample",
        "demod2": "/demods/1/sample",
        "demod3": "/demods/2/sample",
        "demod4": "/demods/3/sample",
        "demod5": "/demods/4/sample",
        "demod6": "/demods/5/sample",
        "demod7": "/demods/6/sample",
        "demod8": "/demods/7/sample",
        "boxcar1": "/boxcars/0/sample",
        "boxcar2": "/boxcars/1/sample",
        "pid1": "/pids/0/stream",
        "pid2": "/pids/1/stream",
        "pid3": "/pids/2/stream",
        "pid4": "/pids/3/stream",
        "aupolar1": "/aupolars/0/sample",
        "aupolar2": "/aupolars/1/sample",
        "aucart1": "/aucarts/0/sample",
        "aucart2": "/aucarts/1/sample",
        "counter1": "/cnts/0/sample",
        "counter2": "/cnts/1/sample",
        "counter3": "/cnts/2/sample",
        "counter4": "/cnts/3/sample",
    },
    "signal_types_demod": {
        "x": "X",
        "y": "Y",
        "r": "R",
        "xiy": "xiy",
        "theta": "Theta",
        "frequency": "Frequency",
        "auxin1": "AuxIn0",
        "auxin2": "AuxIn1",
        "dio": "Dio",
    },
    "signal_types_boxcar": {"": "val"},
    "signal_types_pid": {"error": "Error", "shift": "Shift", "value": "Value"},
    "signal_types_au": {"": "val"},
    "signal_types_counter": {"": "Value"},
    "sweep_parameters": {
        "auxout1offset": "auxouts/0/offset",
        "auxout2offset": "auxouts/1/offset",
        "auxout3offset": "auxouts/2/offset",
        "auxout4offset": "auxouts/3/offset",
        "demdod1phase": "demods/0/phaseshift",
        "demdod2phase": "demods/1/phaseshift",
        "frequency": "oscs/0/freq",
        "output1amp": "sigouts/0/amplitudes/1",
        "output1offset": "sigouts/0/offset",
    },
}


class SweeperModule(Sweeper):
    def signals_list(self):
        return list(MAPPINGS["signal_sources"].keys())

    def sweep_parameter_list(self):
        return list(MAPPINGS["sweep_parameters"].keys())

    def _parse_signals(self, signal_source, **kwargs):
        sources = MAPPINGS["signal_sources"]
        if signal_source.lower() not in sources.keys():
            raise ZHTKException(f"Signal source must be in {list(sources.keys())}")
        signal_node = "/"
        signal_node += self._parent.serial
        signal_node += f"{sources[signal_source]}"
        if kwargs and "pid" in signal_source:
            signal_type = kwargs.get("signal_type", "error")
            types = MAPPINGS["signal_types_pid"]
            if signal_type not in types.keys():
                raise ZHTKException(f"Signal type must be in {list(types.keys())}")
            signal_node += f"/{signal_type}"
        return signal_node.lower()

    def _parse_sweep_param(self, param):
        mapping = MAPPINGS["sweep_parameters"]
        if param not in mapping.keys():
            raise ZHTKException(
                f"The parameter {param} must be one of {list(mapping.keys())}"
            )
        return mapping[param]


class DAQModule(DAQ):
    def signals_list(self):
        return list(MAPPINGS["signal_sources"].keys())

    def _parse_signals(
        self, signal_source, signal_type, operation, fft, complex_selector,
    ):
        # parse 'signal_source'
        signal_source = signal_source.lower()
        signal_type = signal_type.lower()
        sources = MAPPINGS["signal_sources"]
        if signal_source not in sources.keys():
            raise ZHTKException(f"Signal source must be in {sources.keys()}")
        # parse 'signal_type'
        if "demod" in signal_source:
            types = MAPPINGS["signal_types_demod"]
        elif "boxcar" in signal_source:
            types = MAPPINGS["signal_types_boxcar"]
        elif "pid" in signal_source:
            types = MAPPINGS["signal_types_pid"]
        elif "au" in signal_source:
            types = MAPPINGS["signal_types_au"]
        elif "counter" in signal_source:
            types = MAPPINGS["signal_types_counter"]
        if signal_type not in types.keys():
            raise ZHTKException(f"Signal type must be in {types.keys()}")
        # parse 'operation'
        operations = ["replace", "avg", "std"]
        if operation not in operations:
            raise ZHTKException(f"Operation must be in {operations}")
        if operation == "replace":
            operation = ""
        # parse 'fft'
        if fft:
            selectors = ["real", "imag", "phase", "abs"]
            if complex_selector.lower() not in selectors:
                raise ZHTKException(f"Complex selector must be in {selectors}")
        # assemble node
        signal_node = "/"
        signal_node += self._parent.serial
        signal_node += f"{sources[signal_source]}"
        if "pid" not in signal_source:
            signal_node += f".{types[signal_type]}"
        else:
            signal_node += f"/{types[signal_type]}.val"
        if fft:
            signal_node += ".fft"
            signal_node += f".{complex_selector}"
        signal_node += f".{operation}"
        return signal_node.lower()

    def _parse_trigger(self, trigger_source, trigger_type):
        trigger_source = trigger_source.lower()
        trigger_type = trigger_type.lower()
        sources = MAPPINGS["signal_sources"]
        if trigger_source.lower() not in sources.keys():
            raise ZHTKException(f"Signal source must be in {sources.keys()}")
        if trigger_source.lower() == "imp":
            types = MAPPINGS["signal_types_imp"]
        else:
            types = MAPPINGS["signal_types_demod"]
            types.update(
                {"demod2phase": "TrigDemod1Phase",}
            )
        types.update(
            {
                "trigin1": "TrigIn1",
                "trigin2": "TrigIn2",
                "trigout1": "TrigOut1",
                "trigout2": "TrigOut2",
            }
        )
        if trigger_type.lower() not in types.keys():
            raise ZHTKException(f"Signal type must be in {types.keys()}")
        trigger_node = "/"
        trigger_node += self._parent.serial
        trigger_node += f"{sources[trigger_source]}"
        trigger_node += f".{types[trigger_type]}"
        return trigger_node
