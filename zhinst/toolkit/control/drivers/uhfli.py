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
    """High-level driver for Zurich Instruments UHFLI. 
    
    Inherits from BaseInstrument and adds an a Data Acquisition Module, a 
    Sweeper Module and a AWG Module (if option installed). The modules can be 
    accessed as properties of the UHFLI.
    
        >>> import zhinst.toolkit as tk
        >>> uhfli = tk.UHFLI("uhfli", "dev1111")
        >>> uhfli.setup()
        >>> uhfli.connect_device()
        >>> uhfli.nodetree
        >>> ...

    Attributes:
        name (str): Identifier for the UHFLI.
        serial (str): Serial number of the device, e.g. 'dev1234'. The serial 
            number can be found on the back panel of the instrument.
        daq (:class:`zhinst.toolkit.control.drivers.base.DAQModule`)
        sweeper (:class:`zhinst.toolkit.control.drivers.base.SweeperModule`)
        awg (:class:`zhinst.toolkit.control.drivers.uhfqa.AWG`)

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.UHFLI, serial, **kwargs)

    def connect_device(self, nodetree=True):
        """Establishes a device connection.

        Connects the device to a data server and initializes the :class:`DAQModule`, 
        :class:`SweeperModule` and :class:`AWG` (if option installed).
        
        Keyword Arguments:
            nodetree (bool): flag that specifies if all the parameters from the 
                device's nodetree should be added to the object's attributes as 
                :mod:`zhinst-toolkit` :class:`Parameters`. (default: True)

        """
        super().connect_device(nodetree=nodetree)
        self._get_streamingnodes()
        if "AWG" in self._options:
            self._awg = AWG(self, 0)
            self._awg._setup()
        self._daq = DAQModule(self)
        self._daq._setup()
        self._sweeper = SweeperModule(self)
        self._sweeper._setup()

    def _init_settings(self):
        if "AWG" in self.options:
            settings = [
                ("awgs/0/single", 1),
            ]
            self._set(settings)

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


class DAQModule(DAQ):
    """Device-specific Data Acquisition Module for the UHFLI.
    
    Subclasses the DAQ module with parameters that are specific to the MFLI.
    On top of the attributes of the DAQ class, this class defines the 
    `trigger_signals` and `trigger_types` that are used in the 
    `daq.trigger(...)` and `daq.trigger_list()` method. The user is always free 
    to set the parameter `daq.triggernode(..)` directly, however, not all 
    signals can be used as triggers.

        >>> signal = uhfli.daq.signals_add("demod1", "r")
        >>> uhfli.daq.measure()
        >>> ...
        >>> result = uhfli.daq.results[signal]
    
    """

    def __init__(self, parent):
        super().__init__(parent, clk_rate=1.8e9)
        for source in ["auxin", "demod", "cnt"]:
            self._trigger_signals.update(
                {k: v for k, v in self._signal_sources.items() if source in k}
            )
        self._trigger_types = {
            "auxin": {**self._signal_types["auxin"]},
            "cnt": {
                **self._signal_types["cnt"],
                "awgtrigger1": ".TrigAWGTrig1",
                "awgtrigger2": ".TrigAWGTrig2",
                "awgtrigger3": ".TrigAWGTrig3",
                "awgtrigger4": ".TrigAWGTrig4",
                "trigin1": ".TrigIn1",
                "trigin2": ".TrigIn2",
                "trigin3": ".TrigIn3",
                "trigin4": ".TrigIn4",
            },
            "demod": {
                **self._signal_types["demod"],
                "demod4phase": ".TrigDemod4Phase",
                "demod8phase": ".TrigDemod8Phase",
                "awgtrigger1": ".TrigAWGTrig1",
                "awgtrigger2": ".TrigAWGTrig2",
                "awgtrigger3": ".TrigAWGTrig3",
                "awgtrigger4": ".TrigAWGTrig4",
                "trigin1": ".TrigIn1",
                "trigin2": ".TrigIn2",
                "trigin3": ".TrigIn3",
                "trigin4": ".TrigIn4",
                "trigout1": ".TrigOut1",
                "trigout2": ".TrigOut2",
                "trigout3": ".TrigOut3",
                "trigout4": ".TrigOut4",
            },
        }


class SweeperModule(Sweeper):
    """Device-specific Sweeper Module for the UHFLI.

    Subclasses the Sweeper module with parameters that are specific to the MFLI.
    This class defines a dictionary of `sweep_params` which is used for the 
    `sweeper.sweep_parameter(...)` and `sweeper.sweep_parameter_list()` methods. 
    Thos methods and the identifiers (keys in the dict) are mostly guidelines to 
    the user. The parameter to sweep can also be set directly with the 
    `sweeper.gridnode(...)` parameter, however, not all nodes support 
    sweeping. 

        >>> signal = uhfli.sweeper.signals_add("demod1")
        >>> uhfli.sweeper.sweep_parameter("frequency")
        >>> uhfli.sweeper.measure()
        >>> ...
        >>> result = uhfli.sweeper.results[signal]
    
    """

    def __init__(self, parent):
        super().__init__(parent, clk_rate=1.8e9)
        self._sweep_params = {
            "auxout1_offset": "auxouts/0/offset",
            "auxout2_offset": "auxouts/1/offset",
            "auxout3_offset": "auxouts/2/offset",
            "auxout4_offset": "auxouts/3/offset",
            "awg_amplitude1": "awgs/0/outputs/0/amplitude",
            "awg_amplitude2": "awgs/0/outputs/1/amplitude",
            "awg_trigger1": "awgs/0/sweep/awgtrigs/0",
            "awg_trigger2": "awgs/0/sweep/awgtrigs/1",
            "awg_trigger3": "awgs/0/sweep/awgtrigs/2",
            "awg_trigger4": "awgs/0/sweep/awgtrigs/3",
            "awg_triggerlevel1": "awgs/0/triggers/0/level",
            "awg_triggerlevel2": "awgs/0/triggers/1/level",
            "awg_userreg1": "awgs/0/userregs/0",
            "awg_userreg2": "awgs/0/userregs/1",
            "awg_userreg3": "awgs/0/userregs/2",
            "awg_userreg4": "awgs/0/userregs/3",
            "awg_userreg5": "awgs/0/userregs/4",
            "awg_userreg6": "awgs/0/userregs/5",
            "awg_userreg7": "awgs/0/userreg6/6",
            "awg_userreg8": "awgs/0/userregs/7",
            "awg_userreg9": "awgs/0/userregs/8",
            "awg_userreg10": "awgs/0/userregs/9",
            "awg_userreg11": "awgs/0/userregs/10",
            "awg_userreg12": "awgs/0/userregs/11",
            "awg_userreg13": "awgs/0/userregs/12",
            "awg_userreg14": "awgs/0/userregs/13",
            "awg_userreg15": "awgs/0/userregs/14",
            "awg_userreg16": "awgs/0/userregs/15",
            "boxcar1_windowsize": "boxcars/0/windowsize",
            "boxcar1_windowstart": "boxcars/0/windowstart",
            "boxcar2_windowsize": "boxcars/1/windowsize",
            "boxcar2_windowstart": "boxcars/1/windowstart",
            "mod1_carrieramp": "mods/0/carrier/amplitude",
            "mod1_index": "mods/0/index",
            "mod1_sideband1amp": "mods/0/sidebands/0/amplitude",
            "mod1_sideband2amp": "mods/0/sidebands/1/amplitude",
            "mod2_carrieramp": "mods/1/carrier/amplitude",
            "mod2_index": "mods/1/index",
            "mod2_sideband1amp": "mods/1/sidebands/0/amplitude",
            "mod2_sideband2amp": "mods/1/sidebands/1/amplitude",
            "demdod1_phase": "demods/0/phaseshift",
            "demdod2_phase": "demods/1/phaseshift",
            "demdod3_phase": "demods/2/phaseshift",
            "demdod4_phase": "demods/3/phaseshift",
            "demdod5_phase": "demods/4/phaseshift",
            "demdod6_phase": "demods/5/phaseshift",
            "demdod7_phase": "demods/6/phaseshift",
            "demdod8_phase": "demods/7/phaseshift",
            "frequency1": "oscs/0/freq",
            "frequency2": "oscs/1/freq",
            "frequency3": "oscs/2/freq",
            "frequency4": "oscs/3/freq",
            "frequency5": "oscs/4/freq",
            "frequency6": "oscs/5/freq",
            "frequency7": "oscs/6/freq",
            "frequency8": "oscs/7/freq",
            "pid1_setpoint": "pids/0/setpoint",
            "pid2_setpoint": "pids/1/setpoint",
            "pid3_setpoint": "pids/2/setpoint",
            "pid4_setpoint": "pids/3/setpoint",
            "output1_amp": "sigouts/0/amplitudes/1",
            "output1_offset": "sigouts/0/offset",
            "output2_amp": "sigouts/1/amplitudes/1",
            "output2_offset": "sigouts/1/offset",
        }
