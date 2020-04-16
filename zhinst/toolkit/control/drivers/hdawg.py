# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from zhinst.toolkit.control.drivers.base import BaseInstrument, AWGCore, ZHTKException
from zhinst.toolkit.control.nodetree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes
from zhinst.toolkit.helpers import SequenceType, TriggerMode


class HDAWG(BaseInstrument):
    """High-level driver for Zurich Instruments HDAWG. 
    
    Inherits from BaseInstrument and defines device specific methods and 
    properties. The four AWG Cores of the HDAWG can be accessed through the 
    property `awgs` that is a list of four AWGs that are specific for the device 
    and inherit from the `AWGCore` class.

    Typical Usage:
        .. code:: python
        
            import zhinst.toolkit as tk
            hd = tk.HDAWG("hd", "dev2916")
            hd.setup()
            hd.connect_device() 
            hd.awgs[0].run()
            hd.nodetree
            ...

    Arguments:
        name (str): Identifier for the HDAWG.
        serial (str): Serial number of the device, e.g. 'dev1234'. The serial 
            number can be found on the back panel of the instrument.

    Properties:
        awgs (list): list of four AWGs

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.HDAWG, serial, **kwargs)
        self._awgs = [AWG(self, i) for i in range(4)]

    def connect_device(self, nodetree=True):
        """Connects the device to the data server and initializes the AWGs.
        
        Keyword Arguments:
            nodetree (bool): flag that specifies if all the parameters from the 
                device's nodetree should be added to the object's attributes as 
                `zhinst-toolkit` Parameters. (default: True)
        
        """
        super().connect_device(nodetree=nodetree)
        [awg._setup() for awg in self.awgs]

    def _init_settings(self):
        """Sets initial device settings on startup."""
        settings = [
            ("/system/clocks/referenceclock/source", 1),
            ("awgs/*/single", 1),
        ]
        self._set(settings)

    @property
    def awgs(self):
        return self._awgs

    @property
    def _awg_connection(self):
        self._check_connected()
        return self._controller._connection.awg_module


class AWG(AWGCore):
    """Device-specific AWG Core for HDAWG.
    
    This class inherits from the base `AWGCore` and add `zhinst-toolkit` 
    parameters such as ouput, modulation frequency or gains. It also applies 
    sequence specific settings for the HDAWG depending on the type of Sequence 
    Program on the AWG Core.

    Typical Usage:
        >>>hdawg.awgs[0].ouput1("on")
        >>>hdawg.awgs[0].enable_iq_modulation()
        >>>hdawg.awgs[0].modulation_freq()
        >>>Output: 10000.00
        >>>...

    Parameters:
        output1 (str): state of the output 1, i.e. one of {'on', 'off'}
        output2 (str): state of the output 2, i.e. one of {'on', 'off'}
        modulation_freq (float): frequency of the modulation in Hz if IQ 
            modulation enabled 
        modulation_phase_shift (float): phase shift in degrees between I and Q signals if IQ 
            modulation is enabled(default: 90)
        gain1 (flaot): gain of the output channel 1 if IQ modulation is 
            enabled, must be between -1 and +1 (default: +1)
        gain2 (flaot): gain of the output channel 2 if IQ modulation is 
            enabled, must be between -1 and +1 (default: +1)

    """

    def __init__(self, parent, index):
        super().__init__(parent, index)
        self._iq_modulation = False
        self._trigger_level = 0.25
        self.output1 = Parameter(
            self,
            dict(
                Node=f"sigouts/{2*self._index}/on",
                Description="Enables or disables both ouputs of the AWG. Either can be {'1', '0'} or {'on', 'off'}.",
                Type="Integer",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.output2 = Parameter(
            self,
            dict(
                Node=f"sigouts/{2*self._index+1}/on",
                Description="Enables or disables both ouputs of the AWG. Either can be {'1', '0'} or {'on', 'off'}.",
                Type="Integer",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.modulation_freq = Parameter(
            self,
            dict(
                Node=f"oscs/{4 * self._index}/freq",
                Description="Sets the modulation frequency of the AWG output channels.",
                Type="Double",
                Properties="Read, Write",
                Unit="Hz",
            ),
            device=self._parent,
            set_parser=Parse.greater0,
        )
        self.modulation_phase_shift = Parameter(
            self,
            dict(
                Node=f"sines/{2 * self._index + 1}/phaseshift",
                Description="Sets the modulation phase shift between the two AWG output channels.",
                Type="Double",
                Properties="Read, Write",
                Unit="Degrees",
            ),
            device=self._parent,
            set_parser=Parse.phase,
        )
        self.gain1 = Parameter(
            self,
            dict(
                Node=f"awgs/{self._index}/outputs/0/gains/0",
                Description="Sets the gain of the first output channel.",
                Type="Double",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
            set_parser=Parse.amp1,
        )
        self.gain2 = Parameter(
            self,
            dict(
                Node=f"awgs/{self._index}/outputs/1/gains/1",
                Description="Sets the gain of the second output channel.",
                Type="Double",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
            set_parser=Parse.amp1,
        )

    def outputs(self, value=None):
        """Sets both signal outputs simultaneously.
        
        Keyword Arguments:
            value (tuple): Tuple of values {'on', 'off'} for channel 1 and 2 
                (default: {None})
        
        Returns:
            The state {'on', 'off'} for both outputs if the keyword argument is 
            not given.
        
        """
        if value is None:
            return self.output1(), self.output2()
        else:
            if isinstance(value, tuple) or isinstance(value, list):
                if len(value) != 2:
                    raise ZHTKException(
                        "The values should be specified as a tuple, e.g. ('on', 'off')."
                    )
                self.output1(value[0])
                self.output2(value[1])
            else:
                raise ZHTKException("The value must be a tuple or list of length 2!")

    def enable_iq_modulation(self):
        """Enables IQ Modulation by on the AWG Core.
        
        This method applies the corresponding settings for IQ modulation using 
        one of the internal oscillators and two sine generators. The sines are 
        used to modulate the AWG output channels. The parameters 
        `modulation_freq`, `modulation_phase_shift` and `gain1`, `gain2` 
        correspond to the settings of the oscillator and the sine generators. 
        
        """
        self._iq_modulation = True
        i = self._index
        settings = [
            (f"awgs/{i}/outputs/0/modulation/mode", 1),  # modulation: sine 11
            (f"awgs/{i}/outputs/1/modulation/mode", 2),  # modulation: sine 22
            (f"sines/{2 * i}/oscselect", 4 * i),  # select osc N for awg N
            (f"sines/{2 * i + 1}/oscselect", 4 * i),  # select osc N for awg N
            (f"sines/{2 * i + 1}/phaseshift", 90,),  # 90 deg phase shift
        ]
        self._parent._set(settings)
        self.set_sequence_params(reset_phase=True)
        self._parent._set("system/awg/oscillatorcontrol", 1)

    def disable_iq_modulation(self):
        """Disables IQ modulation on the AWG Core.

        Resets the settings of the sine generators and the AWG modulation.

        """
        self._iq_modulation = False
        i = self._index
        settings = [
            (f"awgs/{i}/outputs/0/modulation/mode", 0),  # modulation: sine 11
            (f"awgs/{i}/outputs/1/modulation/mode", 0),  # modulation: sine 22
            (f"sines/{2 * i + 1}/phaseshift", 0,),  # 90 deg phase shift
        ]
        self._parent._set(settings)
        self.set_sequence_params(reset_phase=False)
        self._parent._set("system/awg/oscillatorcontrol", 0)

    def _apply_sequence_settings(self, **kwargs):
        if "sequence_type" in kwargs.keys():
            t = SequenceType(kwargs["sequence_type"])
            allowed_sequences = [
                SequenceType.NONE,
                SequenceType.SIMPLE,
                SequenceType.RABI,
                SequenceType.T1,
                SequenceType.T2,
                SequenceType.CUSTOM,
                SequenceType.TRIGGER,
            ]
            if t not in allowed_sequences:
                raise ZHTKException(
                    f"Sequence type {t} must be one of {allowed_sequences}!"
                )
        if "trigger_mode" in kwargs.keys():
            if TriggerMode(kwargs["trigger_mode"]) == TriggerMode.EXTERNAL_TRIGGER:
                self._apply_trigger_settings()

    def _apply_trigger_settings(self):
        i = self._index
        self._parent._set(f"/triggers/in/{2*i}/level", self._trigger_level)
        self._parent._set(f"/awgs/{i}/auxtriggers/*/channel", 2 * i)
        self._parent._set(f"/awgs/{i}/auxtriggers/*/slope", 1)  # rise

    def __repr__(self):
        s = f"{super().__repr__()}"
        if self._iq_modulation:
            s += f"      IQ Modulation ENABLED:\n"
            s += f"         frequency   : {self.modulation_freq()}\n"
            s += f"         phase_shift : {self.modulation_phase_shift()}\n"
            s += f"         gains       : {self.gain1()}, {self.gain2()}\n"
        else:
            s += f"      IQ Modulation DISABLED\n"
        return s
