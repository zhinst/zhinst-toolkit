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
from zhinst.toolkit.interface import DeviceTypes


"""
High-level controller for MFLI.

"""


class MFLI(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "mfli", serial, **kwargs)

    def connect_device(self, nodetree=True):
        super().connect_device(nodetree=nodetree)
        self._daq_module = DAQModule(self, clk_rate=60e6)
        self._daq_module._setup()
        self._sweeper_module = SweeperModule(self)
        self._sweeper_module._setup()

    def _init_settings(self):
        pass

    @property
    def daq(self):
        return self._daq_module

    @property
    def sweeper(self):
        return self._sweeper_module


MAPPINGS = {
    "signal_sources": {
        "demod1": "/demods/0/sample",
        "demod2": "/demods/1/sample",
        "imp": "/imp/sample",
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
    "signal_types_imp": {
        "real": "RealZ",
        "imag": "ImagZ",
        "abs": "AbsZ",
        "theta": "PhaseZ",
        "frequency": "Frequency",
        "param1": "Param0",
        "param2": "Param1",
    },
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


class DAQModule(DAQ):
    def signals_list(self, source=None):
        if source is None:
            return list(MAPPINGS["signal_sources"].keys())
        else:
            sources = MAPPINGS["signal_sources"]
            if source.lower() not in sources.keys():
                raise ZHTKException(f"Signal source must be in {list(sources.keys())}")
            if "demod" in source:
                return list(MAPPINGS["signal_types_demod"].keys())
            else:
                return list(MAPPINGS["signal_types_imp"].keys())

    def _parse_signals(
        self, signal_source, signal_type, operation, fft, complex_selector,
    ):
        signal_source = signal_source.lower()
        sources = MAPPINGS["signal_sources"]
        if signal_source not in sources.keys():
            raise ZHTKException(f"Signal source must be in {sources.keys()}")
        if signal_source == "imp":
            types = MAPPINGS["signal_types_imp"]
        else:
            types = MAPPINGS["signal_types_demod"]
        if signal_type not in types.keys():
            raise ZHTKException(f"Signal type must be in {types.keys()}")
        operations = ["replace", "avg", "std"]
        if operation not in operations:
            raise ZHTKException(f"Operation must be in {operations}")
        if operation == "replace":
            operation = ""
        if fft:
            selectors = ["real", "imag", "phase", "abs"]
            if complex_selector.lower() not in selectors:
                raise ZHTKException(f"Complex selector must be in {selectors}")
        signal_node = "/"
        signal_node += self._parent.serial
        signal_node += f"{sources[signal_source]}"
        signal_node += f".{types[signal_type]}"
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


class SweeperModule(Sweeper):
    def signals_list(self):
        return list(MAPPINGS["signal_sources"].keys())

    def sweep_parameter_list(self):
        return list(MAPPINGS["sweep_parameters"].keys())

    def _parse_signals(self, signal_source):
        sources = MAPPINGS["signal_sources"]
        if signal_source.lower() not in sources.keys():
            raise ZHTKException(f"Signal source must be in {list(sources.keys())}")
        signal_node = "/"
        signal_node += self._parent.serial
        signal_node += f"{sources[signal_source]}"
        return signal_node.lower()

    def _parse_sweep_param(self, param):
        mapping = MAPPINGS["sweep_parameters"]
        if param not in mapping.keys():
            raise ZHTKException(
                f"The parameter {param} must be one of {list(mapping.keys())}"
            )
        return mapping[param]
