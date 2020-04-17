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


class MFLI(BaseInstrument):
    """High-level driver for the Zurich Instruments MFLI. 
    
    Inherits from :class:`BaseInstrument` and adds a :class:`DAQModule` and a 
    :class:`SweeperModule`. They can be accessed as properties of the MFLI.

        >>> import zhinst.toolkit as tk
        >>> mfli = tk.MFLI("mfli", "dev1234")
        >>> mfli.setup()
        >>> mfli.connect_device()
        >>> mfli.nodetree
        ...

        >>> signal = mfli.daq.signals_add("demod1", "r")
        >>> mfli.daq.measure()
        ...
        >>> result = mfli.daq.results[signal]
        
        >>> signal = mfli.sweeper.signals_add("demod1")
        >>> mfli.sweeper.sweep_parameter("frequency")
        >>> mfli.sweeper.measure()
        ...
        >>> result = mfli.sweeper.results[signal]

    Attributes:
        name (str): Identifier for the MFLI.
        serial (str): Serial number of the device, e.g. 'dev1234'. The serial 
            number can be found on the back panel of the instrument.
        daq (:class:`zhinst.toolkit.control.drivers.base.DAQModule`)
        sweeper (:class:`zhinst.toolkit.control.drivers.base.SweeperModule`)

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.MFLI, serial, **kwargs)

    def connect_device(self, nodetree=True):
        """Establishes the device connection.
        
        Connects the device to the data server and initializes the DAQModule and 
        SweeperModule.

        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from 
                the nodetree should be added to the object's attributes as 
                `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)
        self._get_streamingnodes()
        self._daq_module = DAQModule(self)
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


class DAQModule(DAQ):
    """Device-specific Data Acquisition Module for the MFLI.
    
    Subclasses the DAQ module with parameters that are specific to the MFLI.
    On top of the attributes of the DAQ class, this class defines the 
    `trigger_signals` and `trigger_types` that are used in the 
    `daq.trigger(...)` and `daq.trigger_list()` method. The user is always free 
    to set the parameter `daq.triggernode(..)` directly, however, not all 
    signals can be used as triggers.

        >>> signal = mfli.daq.signals_add("demod1", "r")
        >>> mfli.daq.measure()
        >>> ...
        >>> result = mfli.daq.results[signal]
    
    """

    def __init__(self, parent):
        super().__init__(parent, clk_rate=1.8e9)
        self._trigger_signals = {}
        for source in ["auxin", "demod", "imp"]:
            self._trigger_signals.update(
                {k: v for k, v in self._signal_sources.items() if source in k}
            )
        self._trigger_types = {
            "demod": {
                **self._signal_types["demod"],
                "demod2phase": ".TrigDemod2Phase",
                "trigin1": ".TrigIn1",
                "trigin2": ".TrigIn2",
                "trigout1": ".TrigOut1",
                "trigout2": ".TrigOut2",
            },
            "imp": {
                **self._signal_types["imp"],
                "trigin1": ".TrigIn1",
                "trigin2": ".TrigIn2",
                "trigout1": ".TrigOut1",
                "trigout2": ".TrigOut2",
            },
        }


class SweeperModule(Sweeper):
    """Device-specific Sweeper Module for the MFLI.

    Subclasses the Sweeper module with parameters that are specific to the MFLI.
    This class defines a dictionary of `sweep_params` which is used for the 
    `sweeper.sweep_parameter(...)` and `sweeper.sweep_parameter_list()` methods. 
    Thos methods and the identifiers (keys in the dict) are mostly guidelines to 
    the user. The parameter to sweep can also be set directly with the 
    `sweeper.gridnode(...)` parameter, however, not all nodes support 
    sweeping. 

        >>> signal = mfli.sweeper.signals_add("demod1")
        >>> mfli.sweeper.sweep_parameter("frequency")
        >>> mfli.sweeper.measure()
        >>> ...
        >>> result = mfli.sweeper.results[signal]
    
    """

    def __init__(self, parent):
        super().__init__(parent, clk_rate=60e6)
        self._sweep_params = {
            "auxout1offset": "auxouts/0/offset",
            "auxout2offset": "auxouts/1/offset",
            "auxout3offset": "auxouts/2/offset",
            "auxout4offset": "auxouts/3/offset",
            "demdod1phase": "demods/0/phaseshift",
            "demdod2phase": "demods/1/phaseshift",
            "frequency": "oscs/0/freq",
            "output1amp": "sigouts/0/amplitudes/1",
            "output1offset": "sigouts/0/offset",
        }
