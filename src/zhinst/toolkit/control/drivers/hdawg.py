# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from zhinst.toolkit.control.drivers.base import BaseInstrument, AWGCore, ToolkitError
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes
from zhinst.toolkit.helpers import SequenceType, TriggerMode


class HDAWG(BaseInstrument):
    """High-level driver for Zurich Instruments HDAWG. 
    
    Inherits from :class:`BaseInstrument` and defines device specific methods and 
    properties. The four AWG Cores of the :class:`HDAWG` can be accessed through the 
    property `awgs` that is a list of four :class:`AWGCore` s that are specific for the device 
    and inherit from the :class:`AWGCore` class.

        >>> from zhinst.toolkit import HDAWG
        >>> ... 
        >>> hd = HDAWG("hdawg 1", "dev8030")
        >>> hd.setup()
        >>> hd.connect_device()
        >>> hd.nodetree
        <zhinst.toolkit.tools.node_tree.NodeTree object at 0x0000021E467D3BA8>
        nodes:
        - stats
        - oscs
        - status
        - sines
        - awgs
        - dio
        - system
        - sigouts
        - triggers
        - features
        - cnts
        parameters:
        - clockbase


    Arguments:
        name (str): Identifier for the HDAWG.
        serial (str): Serial number of the device, e.g. *'dev1234'*. The serial 
            number can be found on the back panel of the instrument.
        discovery: an instance of ziDiscovery

    Attributes:
        awgs (list): A list of four device-specific AWG Cores of type 
            :class:`zhinst.toolkit.control.drivers.hdawg.AWG`.

    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.HDAWG, serial, discovery, **kwargs)
        self._awgs = [AWG(self, i) for i in range(4)]

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server and initializes the AWGs.
        
        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from 
                the device's nodetree should be added to the object's attributes 
                as `zhinst-toolkit` Parameters. (default: True)
        
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


class AWG(AWGCore):
    """Device-specific AWG Core for HDAWG.
    
    This class inherits from the base :class:`AWGCore` and adds 
    :mod:`zhinst-toolkit` :class:`Parameters` such as ouput, modulation 
    frequency or gains. It also applies sequence specific settings for the 
    HDAWG, depending on the type of :class:`SequenceProgram` on the AWG Core.

        >>> hd.awgs[0]
        <zhinst.toolkit.hdawg.AWG object at 0x0000021E467D3320>
            parent  : <zhinst.toolkit.hdawg.HDAWG object at 0x0000021E467D3198>
            index   : 0
            sequence: 
                    type: None
                    ('target', 'hdawg')
                    ('clock_rate', 2400000000.0)
                    ('period', 0.0001)
                    ('trigger_mode', 'None')
                    ('repetitions', 1)
                    ('alignment', 'End with Trigger')
                    ...
        
        >>> hd.awgs[0].outputs("on")
        >>> hd.awgs[0].enable_iq_modulation()
        >>> hd.awgs[0].modulation_freq(123.45e6)
        >>> hd.awgs[0].gain1()
        1.0

    See more about AWG Cores at 
    :class:`zhinst.toolkit.control.drivers.base.AWGCore`.

    Attributes:
        output1 (:class:`Parameter`): State of the output 1, i.e. one of 
            {'on', 'off'}.
        output2 (:class:`Parameter`): State of the output 2, i.e. one of 
            {'on', 'off'}.
        modulation_freq (:class:`Parameter`): Frequency of the modulation in 
            Hz if IQ modulation is enabled. 
        modulation_phase_shift (:class:`Parameter`): Phase shift in degrees 
            between I and Q quadratures if IQ modulation is enabled 
            (default: 90).
        gain1 (:class:`Parameter`): Gain of the output channel 1 if IQ 
            modulation is enabled. Must be between -1 and +1 (default: +1).
        gain2 (:class:`Parameter`): Gain of the output channel 2 if IQ 
            modulation is enabled. Must be between -1 and +1 (default: +1).

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
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
                (default: None).
        
        Returns:
            A tuple with the states {'on', 'off'} for the two output channels if 
            the keyword argument is not given.
        
        """
        if value is None:
            return self.output1(), self.output2()
        else:
            if isinstance(value, tuple) or isinstance(value, list):
                if len(value) != 2:
                    raise ToolkitError(
                        "The values should be specified as a tuple, e.g. ('on', 'off')."
                    )
                self.output1(value[0])
                self.output2(value[1])
            else:
                raise ToolkitError("The value must be a tuple or list of length 2!")

    def enable_iq_modulation(self) -> None:
        """Enables IQ Modulation on the AWG Core.
        
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

    def disable_iq_modulation(self) -> None:
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
                raise ToolkitError(
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
