import numpy as np

from .base import BaseInstrument
from .awg_core import AWGCore
from .tools import ZHTKException, Parameter
import tools.parsers as parse


class HDAWG(BaseInstrument):
    """
    High-level controller for HDAWG. Inherits from BaseInstrument and defines 
    device specific methods. The property awg_connection accesses the 
    connection's awg module and is used in the AWG core as 
    awg._parent._awg_module. 

    The device has four awg cores that can be used as

        import zhinst.toolkit as tk
        hd = tk.HDAWG("hd", "dev2916")
        hd.setup()
        hd.connect_device()
        
        hd.awgs[0].run()
        ...

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "hdawg", serial, **kwargs)
        self._awgs = [AWG(self, i) for i in range(4)]

    def set_outputs(self, values):
        assert len(values) == 4
        [self.awgs[i].set_output(v) for i, v in enumerate(values)]

    def set_modulation_frequencies(self, frequencies):
        assert len(frequencies) <= 4
        [self.awgs[i].set_modulation_frequency(f) for i, f in enumerate(frequencies)]

    def set_modulation_phases(self, phases):
        assert len(phases) <= 4
        [self.awgs[i].set_modulation_phase(p) for i, p in enumerate(phases)]

    def set_modulation_gains(self, gains):
        assert len(gains) <= 4
        [self.awgs[i].set_modulation_gain(g) for i, g in enumerate(gains)]

    def _init_settings(self):
        settings = [
            ("/dev8030/system/clocks/referenceclock/source", 1,),
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
    """
    Device-specific AWG for HDAWG with properties like ouput, modulation frequency or gains and 
    sequence specific settings for the HDAWG. Inherits from AWGCore.

    """

    def __init__(self, parent, index):
        super().__init__(parent, index)
        self._iq_modulation = False
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
            set_parser=parse.set_on_off,
            get_parser=parse.get_on_off,
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
            set_parser=parse.set_on_off,
            get_parser=parse.get_on_off,
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
            set_parser=parse.greater0,
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
            set_parser=parse.abs90,
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
            set_parser=parse.amp1,
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
            set_parser=parse.amp1,
        )

    def outputs(self, value=None):
        if value is None:
            return self.output1(), self.output2()
        else:
            self.output1(value)
            self.output2(value)

    def enable_iq_modulation(self):
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

    def disable_iq_modulation(self):
        self._iq_modulation = False
        i = self._index
        settings = [
            (f"awgs/{i}/outputs/0/modulation/mode", 0),  # modulation: sine 11
            (f"awgs/{i}/outputs/1/modulation/mode", 0),  # modulation: sine 22
            (f"sines/{2 * i + 1}/phaseshift", 0,),  # 90 deg phase shift
        ]
        self._parent._set(settings)

    def _apply_sequence_settings(self, **kwargs):
        if "sequence_type" in kwargs.keys():
            t = kwargs["sequence_type"]
            allowed_sequences = [
                "None",
                "Simple",
                "Rabi",
                "T1",
                "T2*",
                "Custom",
            ]
            if t not in allowed_sequences:
                raise ZHTKException(
                    f"Sequence type {t} must be one of {allowed_sequences}!"
                )
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self._apply_trigger_settings()

    def _apply_trigger_settings(self):
        i = self._index
        self._parent._set(f"/trigger/in/{2*i}/level", 0.5)
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

