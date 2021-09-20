# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from zhinst.toolkit.control.drivers.base import (
    BaseInstrument,
    AWGCore,
    CommandTable,
)
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
from zhinst.toolkit.helpers import SequenceType, TriggerMode

_logger = LoggerModule(__name__)


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
        serial (str): Serial number of the device, e.g. *'dev8000'*. The serial
            number can be found on the back panel of the instrument.
        discovery: an instance of ziDiscovery

    Attributes:
        awgs (list): A list of four device-specific AWG Cores of type
            :class:`zhinst.toolkit.control.drivers.hdawg.AWG`.
        allowed_sequences (list): A list of :class:`SequenceType` s
            that the instrument supports.
        allowed_trigger_modes (list): A list of :class:`TriggerMode` s
            that the instrument supports.
        ref_clock (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Clock source used as the frequency and time base reference.
            Either `0: "internal"`, `1: "external"` or `2: "zsync"`.
            `0: "internal`: Internal 10 MHz clock
            `1: "external`: An external clock. Provide a clean and stable
            10 MHz or 100 MHz reference to the appropriate back panel
            connector.
            `2: "zsync`: A ZSync clock is intended to be used.
        ref_clock_status (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Status of the reference clock. Either `0: "locked"`,
            `1: "error"` or `2: "busy"`.
    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.HDAWG, serial, discovery, **kwargs)
        self._awgs = []
        self.ref_clock = None
        self.ref_clock_status = None
        self._allowed_sequences = [
            SequenceType.NONE,
            SequenceType.SIMPLE,
            SequenceType.TRIGGER,
            SequenceType.RABI,
            SequenceType.T1,
            SequenceType.T2,
            SequenceType.CUSTOM,
        ]
        self._allowed_trigger_modes = [
            TriggerMode.NONE,
            TriggerMode.SEND_TRIGGER,
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
            TriggerMode.SEND_AND_RECEIVE_TRIGGER,
            TriggerMode.ZSYNC_TRIGGER,
        ]

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server and initializes the AWGs.

        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from
                the device's nodetree should be added to the object's attributes
                as `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)
        self._init_awg_cores()

    def factory_reset(self, sync=True) -> None:
        """Load the factory default settings.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).

        """
        super().factory_reset(sync=sync)

    def enable_qccs_mode(self) -> None:
        """Configure the instrument to work with PQSC

        This method sets the reference clock source and DIO settings
        correctly to connect the instrument to the PQSC.
        """
        settings = [
            # Set ZSync clock to be used as reference
            ("/system/clocks/referenceclock/source", "zsync"),
            # Configure DIO
            # Set interface standard to use on the 32-bit DIO to LVCMOS
            ("/dios/0/interface", 0),
            # Set DIO output values to ZSync input values.
            # Forward the ZSync input values to the AWG sequencer.
            # Forward the DIO input values to the ZSync output.
            ("/dios/0/mode", "qccs"),
            # Drive the two most significant bytes of the DIO port
            ("/dios/0/drive", 0b1100),
        ]
        self._set(settings)

    def enable_manual_mode(self) -> None:
        """Disconnect from PQSC

        This method sets the reference clock source and DIO settings to
        factory default states and the instrument is disconnected from
        the PQSC.
        """
        settings = [
            # Set internal clock to be used as reference
            ("/system/clocks/referenceclock/source", "internal"),
            # Configure DIO settigns to factory default values
            # Set interface standard to use on the 32-bit DIO to LVCMOS
            ("/dios/0/interface", 0),
            # Enable manual control of the DIO output bits
            ("/dios/0/mode", "manual"),
            # Disable drive for all DIO bits
            ("/dios/0/drive", 0b0000),
        ]
        self._set(settings)

    def num_awg_cores(self):
        """Find the number of AWG Cores available in the instrument."""
        serial = self.serial
        daq = self._controller.connection.daq
        cores = daq.listNodes(f"{serial}/awgs/")
        return len(cores)

    def _init_awg_cores(self):
        """Initialize the AWGs cores of the device."""
        self._awgs = [AWG(self, i) for i in range(self.num_awg_cores())]
        [awg._setup() for awg in self.awgs]
        [awg._init_awg_params() for awg in self.awgs]
        [
            awg._init_ct(
                "https://docs.zhinst.com/hdawg/commandtable/v2/schema",
                f"awgs/{awg._index}/commandtable",
            )
            for awg in self.awgs
        ]

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        super()._init_params()
        self.ref_clock = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/source"),
            device=self,
            auto_mapping=True,
        )
        self.ref_clock_status = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/status"),
            device=self,
            get_parser=Parse.get_locked_status,
        )

    def _init_settings(self):
        """Sets initial device settings on startup."""
        pass

    @property
    def awgs(self):
        return self._awgs

    @property
    def allowed_sequences(self):
        return self._allowed_sequences

    @property
    def allowed_trigger_modes(self):
        return self._allowed_trigger_modes


class AWG(AWGCore):
    """Device-specific AWG Core for HDAWG.

    This class inherits from the base :class:`AWGCore` and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s such as output,
    modulation frequency or gains. It also applies sequence specific
    settings for the HDAWG, depending on the type of
    :class:`SequenceProgram` on the AWG Core.

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

        >>> hd.awgs[0].outputs(["on", "on"])
        >>> hd.awgs[0].single(True)
        >>> hd.awgs[0].enable_iq_modulation()
        >>> hd.awgs[0].modulation_freq(123.45e6)
        >>> hd.awgs[0].gain1()
        1.0

    Command table data can be specified and uploaded to the AWG core as
    follows:

        >>> command_table = []
        >>> command_table.append(
        >>>    {
        >>>        "index": 0,
        >>>        "waveform": {"index": 0},
        >>>        "amplitude0": {"value": 1.0, "increment": False},
        >>>    }
        >>> )
        >>> command_table.append(
        >>>    {
        >>>        "index": 1,
        >>>        "waveform": {"index": 0},
        >>>        "amplitude0": {"value": 0.5, "increment": False},
        >>>    }
        >>> )
        >>> hd.awgs[0].ct.load(command_table)


    See more about AWG Cores at
    :class:`zhinst.toolkit.control.drivers.base.AWGCore`.

    Attributes:
        ct (:class:`zhinst.toolkit.control.drivers.hdawg.CT`):
            A device-specific :class:`CommandTable` for the HDAWG.
        output1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the output 1, i.e. one of {'on', 'off'}.
        output2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the output 2, i.e. one of {'on', 'off'}.
        modulation_freq (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Frequency of the modulation in Hz if IQ modulation is enabled.
        modulation_phase_shift (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Phase shift in degrees between I and Q quadratures if IQ
            modulation is enabled (default: 90).
        gain1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the output channel 1 if IQ modulation is enabled.
            Must be between -1 and +1 (default: +1).
        gain2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the output channel 2 if IQ modulation is enabled.
            Must be between -1 and +1 (default: +1).
        single (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the AWG single shot mode, i.e. one of
            {True, False} (default: True).
        zsync_register_mask (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Register mask configuration to select only the portion of
            interest of the register output forwarded from the PQSC to
            the HDAWG. Can be between 0 and 15 (default: 0).
        zsync_register_shift (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Register shift configuration to select only the portion of
            interest of the register output forwarded from the PQSC to
            the HDAWG. Can be between 0 and 3 (default: 0).
        zsync_register_offset (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Register offset configuration to select the base index of
            the command table to be addressed. Can be between 0 and 1023
            (default: 0).
        zsync_decoder_mask (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Decoder mask configuration to select only the portion of
            interest of the decoder output forwarded from the PQSC to
            the HDAWG. Can be between 0 and 255 (default: 0).
        zsync_decoder_shift (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Decoder shift configuration to select only the portion of
            interest of the decoder output forwarded from the PQSC to
            HDAWG. Can be between 0 and 7 (default: 0).
        zsync_decoder_offset (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Decoder offset configuration to select the base index of the
            command table to be addressed. Can be between 0 and 1023
            (default: 0).
    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        super().__init__(parent, index)
        self._enable = None
        self._ct = None
        self._iq_modulation = False
        self.output1 = None
        self.output2 = None
        self.modulation_freq = None
        self.modulation_phase_shift = None
        self.gain1 = None
        self.gain2 = None
        self.single = None
        self.zsync_register_mask = None
        self.zsync_register_shift = None
        self.zsync_register_offset = None
        self.zsync_decoder_mask = None
        self.zsync_decoder_shift = None
        self.zsync_decoder_offset = None

    def _init_awg_params(self):
        self._enable = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.output1 = Parameter(
            self,
            self._parent._get_node_dict(f"sigouts/{2*self._index}/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.output2 = Parameter(
            self,
            self._parent._get_node_dict(f"sigouts/{2*self._index+1}/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        # If the HDAWG has the MF option, the oscillator assignment
        # per core is different
        if "MF" in self._parent.options:
            oscs_multiplier = 4
        else:
            oscs_multiplier = 1
        self.modulation_freq = Parameter(
            self,
            self._parent._get_node_dict(f"oscs/{oscs_multiplier* self._index}/freq"),
            device=self._parent,
            set_parser=lambda v: Parse.greater(v, 0),
        )
        self.modulation_phase_shift = Parameter(
            self,
            self._parent._get_node_dict(f"sines/{2 * self._index + 1}/phaseshift"),
            device=self._parent,
            set_parser=Parse.phase,
        )
        self.gain1 = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/outputs/0/gains/0"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.gain2 = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/outputs/1/gains/1"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.single = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/single"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.zsync_register_mask = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/zsync/register/mask"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 15),
                lambda v: Parse.greater_equal(v, 0),
            ],
        )
        self.zsync_register_shift = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/zsync/register/shift"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 3),
                lambda v: Parse.greater_equal(v, 0),
            ],
        )
        self.zsync_register_offset = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/zsync/register/offset"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1023),
                lambda v: Parse.greater_equal(v, 0),
            ],
        )
        self.zsync_decoder_mask = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/zsync/decoder/mask"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 255),
                lambda v: Parse.greater_equal(v, 0),
            ],
        )
        self.zsync_decoder_shift = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/zsync/decoder/shift"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 7),
                lambda v: Parse.greater_equal(v, 0),
            ],
        )
        self.zsync_decoder_offset = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/{self._index}/zsync/decoder/offset"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1023),
                lambda v: Parse.greater_equal(v, 0),
            ],
        )

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
            (f"sines/{2 * i + 1}/phaseshift", 90),  # 90 deg phase shift
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
            (f"sines/{2 * i + 1}/phaseshift", 0),  # 0 deg phase shift
        ]
        self._parent._set(settings)
        self.set_sequence_params(reset_phase=False)
        self._parent._set("system/awg/oscillatorcontrol", 0)

    def _apply_sequence_settings(self, **kwargs) -> None:
        super()._apply_sequence_settings(**kwargs)
        if "trigger_mode" in kwargs.keys() and kwargs["trigger_mode"] != "None":
            t = TriggerMode(kwargs["trigger_mode"])
            # apply settings depending on trigger mode
            if t in [TriggerMode.EXTERNAL_TRIGGER, TriggerMode.RECEIVE_TRIGGER]:
                self._apply_receive_trigger_settings()
            elif t == TriggerMode.ZSYNC_TRIGGER:
                self._apply_zsync_trigger_settings()

    def _apply_receive_trigger_settings(self):
        i = self._index
        self._parent._set(f"/awgs/{i}/auxtriggers/*/channel", 2 * i)
        self._parent._set(f"/awgs/{i}/auxtriggers/*/slope", 1)  # rise

    def _apply_zsync_trigger_settings(self):
        i = self._index
        settings = [
            # Configure DIO trigger
            # Set signal edge of the STROBE signal to off
            (f"/awgs/{i}/dio/strobe/slope", "off"),
            # Ignore VALID bit, trigger on any valid input
            (f"/awgs/{i}/dio/valid/polarity", "none"),
        ]
        self._parent._set(settings)

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
