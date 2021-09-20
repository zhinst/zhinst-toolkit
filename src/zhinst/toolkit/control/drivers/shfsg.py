# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import math

from zhinst.toolkit.control.drivers.base import (
    BaseInstrument,
    AWGCore,
)
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
from zhinst.toolkit.helpers import SequenceType, TriggerMode

_logger = LoggerModule(__name__)


class SHFSG(BaseInstrument):
    """High-level driver for Zurich Instruments SHFSG.

    Inherits from :class:`BaseInstrument` and defines device specific methods and
    properties.

        >>> from zhinst.toolkit import SHFSG
        >>> ...
        >>> shfsg = SHFSG("shfsg1", "dev12000")
        >>> shfsg.setup()
        >>> shfsg.connect_device()
        >>> shfsg.nodetree
        <zhinst.toolkit.tools.node_tree.NodeTree object at 0x0000021E467D3BA8>
        nodes:
        - stats
        - status
        - system
        - features
        - synthesizers
        - sgchannels
        - dio
        parameters:
        - clockbase

    Arguments:
        name (str): Identifier for the SHFSG.
        serial (str): Serial number of the device, e.g. *'dev12000'*. The serial
            number can be found on the back panel of the instrument.
        discovery: an instance of ziDiscovery (default = None)

    Attributes:
        sgchannels (list): A list of four/eight signal channels
            :class:`zhinst.toolkit.control.drivers.shfsg.sgchannel`.
        allowed_sequences (list): A list of :class:`SequenceType` s
            that the instrument supports.
        allowed_trigger_modes (list): A list of :class:`TriggerMode` s
            that the instrument supports.
    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.SHFSG, serial, discovery, **kwargs)
        self._sgchannels = []
        self.ref_clock = None
        self.ref_clock_status = None
        self.ref_clock_out = None
        self.ref_clock_out_freq = None

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

    def check_ref_clock(
        self, blocking: bool = True, timeout: int = 30, sleep_time: int = 1
    ) -> None:
        """Check if reference clock is locked successfully.

        Arguments:
            blocking (bool): A flag that specifies if the program should
                be blocked until the reference clock is 'locked'.
                (default: True)
            timeout (int): Maximum time in seconds the program waits
                when `blocking` is set to `True` (default: 30).
            sleep_time (int): Time in seconds to wait between
                requesting the reference clock status (default: 1)

        Raises:
            ToolkitError: If the device fails to lock on the reference
                clock.

        """
        self._check_ref_clock(blocking=blocking, timeout=timeout, sleep_time=sleep_time)

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server and initializes the AWGs.

        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from
                the device's nodetree should be added to the object's attributes
                as `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)
        self._init_sgchannels()

    def factory_reset(self, sync=True) -> None:
        """Load the factory default settings.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).

        """
        _logger.warning(
            f"Factory preset is not yet supported in SHFSG" f"{self.serial.upper()}."
        )

    def enable_qccs_mode(self) -> None:
        """Configure the instrument to work with PQSC

        This method sets the reference clock source to
        connect the instrument to the PQSC.
        """
        self._set("/system/clocks/referenceclock/in/source", 2)

    def enable_manual_mode(self) -> None:
        """Configure the instrument to work without external triggers/devices

        This method sets the reference clock source to internal.
        """
        self._set("/system/clocks/referenceclock/in/source", 0)

    def num_sgchannels(self):
        """Find the number of sgchannels available in the instrument."""
        serial = self.serial
        daq = self._controller.connection.daq
        qachannels = daq.listNodes(f"{serial}/sgchannels/")
        return len(qachannels)

    def _init_sgchannels(self):
        """Initialize the SGChannel cores of the device."""
        self._sgchannels = [SGChannel(self, i) for i in range(self.num_sgchannels())]
        [sgchannel._setup() for sgchannel in self._sgchannels]
        [sgchannel._init_sgchannel_params() for sgchannel in self._sgchannels]
        [
            sgchannel.awg._init_ct(
                "https://docs.zhinst.com/shfsg/commandtable/v1_0/schema",
                f"sgchannels/{sgchannel._index}/awg/commandtable",
            )
            for sgchannel in self._sgchannels
        ]

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        super()._init_params()
        self.ref_clock = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/source"),
            device=self,
            auto_mapping=True,
        )
        self.ref_clock_status = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/status"),
            device=self,
            get_parser=Parse.get_locked_status,
        )
        self.ref_clock_out = Parameter(
            self,
            self._get_node_dict("system/clocks/referenceclock/out/enable"),
            device=self,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.ref_clock_out_freq = Parameter(
            self,
            self._get_node_dict("system/clocks/referenceclock/out/freq"),
            device=self,
            set_parser=lambda v: Parse.greater(v, 0),
        )
    def _init_settings(self):
        """Sets initial device settings on startup."""
        pass

    @property
    def sgchannels(self):
        return self._sgchannels

    @property
    def allowed_sequences(self):
        return self._allowed_sequences

    @property
    def allowed_trigger_modes(self):
        return self._allowed_trigger_modes


class SGChannel:
    """Signal Channel for SHFSG.
    This class pepresents a single signal channel for the SHFSG.
    It hold a Device-specific AWG Core for SHFSG, gives an easy
    access to configure the Sine channel and offers functionality
    to control the output.

    Attributes:
        awg (:class:`zhinst.toolkit.control.drivers.shfsg.AWG`):
            A device-specific :class:`AWGCore` for the SHFSG
        sine (:class:`zhinst.toolkit.control.drivers.shfsg.Sine`):
            class to controll the Sine Channel for the SHFSG
        output (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the output, i.e. one of {'on', 'off'}.
        output_range (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Maximal Range of the Signal Output power.
            The instrument selects the closest available Range with a resolution of 5 dBm
        rf_center_freq (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The Center Frequency of the synthesizer.
        digital_mixer_center_freq (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The Center Frequency of the digital_mixer. ()
        rf_or_lf_path (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Switch between RF and LF output path.
        marker_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Assign a signal to the marker.
    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        self._parent = parent
        self._index = index
        self.awg = AWG(parent, index)
        self.sine = Sine(parent, index, 0)
        self.output = None
        self.output_range = None
        self.rf_center_freq = None
        self.digital_mixer_center_freq = None
        self.rf_or_lf_path = None
        self.marker_source = None

    def _setup(self):
        self.awg._setup()
        self.sine._setup()

    def _init_sgchannel_params(self):
        self.awg._init_awg_params()

        self.output = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/output/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )

        self.output_range = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/output/range"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, -30),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        )

        self.rf_center_freq = Parameter(
            self,
            self._parent._get_node_dict(
                f"synthesizers/{math.floor(self._index/2)}/centerfreq"
            ),
            device=self._parent,
            set_parser=lambda v: Parse.greater(v, 0),
        )

        # self.digital_mixer_center_freq = Parameter(
        #     self,
        #     self._parent._get_node_dict(
        #         f"sgchannels/{self._index}/digitalmixer/centerfreq"
        #     ),
        #     device=self._parent,
        #     set_parser=lambda v: Parse.greater(v, 0),
        # )

        self.rf_or_lf_path = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/output/rflfpath"),
            device=self._parent,
            set_parser=Parse.set_rf_lf,
            get_parser=Parse.get_rf_lf,
        )

        self.marker_source = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/marker/source"),
            device=self._parent,
            auto_mapping=True,
        )

class AWG(AWGCore):
    """Device-specific AWG Core for SHFSG.

    This class inherits from the base :class:`AWGCore` and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s such as output,
    modulation frequency or gains. It also applies sequence specific
    settings for the SHFSG, depending on the type of
    :class:`SequenceProgram` on the AWG Core.

        >>> shfsg.sgchannels[0].awg
        <zhinst.toolkit.control.drivers.shfsg.AWG object at 0x11ba77550>
            parent  : <zhinst.toolkit.control.drivers.shfsg.SHFSG object at 0x10c6d2d00>
            index   : 0
            sequence:
                    type: SequenceType.NONE
                    ('target', <DeviceTypes.SHFSG: 'shfsg'>)
                    ('clock_rate', 2000000000.0)
                    ('period', 0.0001)
                    ('trigger_mode', <TriggerMode.SEND_TRIGGER: 'Send Trigger'>)
                    ('trigger_samples', 32)
                    ('repetitions', 1)
                    ('alignment', <Alignment.END_WITH_TRIGGER: 'End with Trigger'>)
                    ...

        >>> shfsg.sgchannels[0].output("on")
        >>> shfsg.sgchannels[0].awg.single(True)
        >>> shfsg.sgchannels[0].awg.enable_iq_modulation()
        >>> shfsg.sgchannels[0].awg.modulation_freq(123.45e6)
        >>> shfsg.sgchannels[0].awg.gain1()
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
        >>> shfsg.sgchannels[0].awg.ct.load(command_table)


    See more about AWG Cores at
    :class:`zhinst.toolkit.control.drivers.base.AWGCore`.

    Attributes:
        ct (:class:`zhinst.toolkit.control.drivers.shfsg.CT`):
            A device-specific :class:`CommandTable` for the SHFSG.
        output1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the output 1, i.e. one of {'on', 'off'}.
        output2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the output 2, i.e. one of {'on', 'off'}.
        modulation_freq (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Frequency of the modulation in Hz if IQ modulation is enabled.
        modulation_phase_shift (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Phase shift in degrees between I and Q quadratures if IQ
            modulation is enabled (default: 90).
        gain00 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the I output channel 1 if IQ modulation is enabled.
            Must be between -1 and +1 (default: +1).
        gain01 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the Q output channel 1 if IQ modulation is enabled.
            Must be between -1 and +1 (default: +1).
        gain10 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the I output channel 2 if IQ modulation is enabled.
            Must be between -1 and +1 (default: +1).
        gain11 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the Q output channel 2 if IQ modulation is enabled.
            Must be between -1 and +1 (default: +1).
        single (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the AWG single shot mode, i.e. one of
            {True, False} (default: True).
        digital_trigger1_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Selects the digital trigger 1 source signal. (default: 0)
        digital_trigger2_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Selects the digital trigger 1 source signal. (default: 0)
        digital_trigger1_slope (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the signal edge that should activate the trigger.
            The trigger will be level sensitive when the Level option is selected.
            ("level_sensitive", "rising_edge" , "falling_edge", "both_edges" (default: 0)
        digital_trigger2_slope (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the signal edge that should activate the trigger.
            The trigger will be level sensitive when the Level option is selected.
            ("level_sensitive", "rising_edge" , "falling_edge", "both_edges" (default: 0)
    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        super().__init__(parent, index)
        self._enable = None
        self._iq_modulation = False
        self.output1 = None
        self.output2 = None
        self.modulation_freq = None
        self.modulation_phase_shift = None
        self.gain00 = None
        self.gain01 = None
        self.gain10 = None
        self.gain11 = None
        self.single = None
        self.digital_trigger1_source = None
        self.digital_trigger2_source = None
        self.digital_trigger1_slope = None
        self.digital_trigger2_slope = None
        # TODO Right now not available/needed on the shfsg
        # self.zsync_register_mask = None
        # self.zsync_register_shift = None
        # self.zsync_register_offset = None
        # self.zsync_decoder_mask = None
        # self.zsync_decoder_shift = None
        # self.zsync_decoder_offset = None

    def _get_modulation_freq_node(self):
        selected_osc = self._parent._get(f"sgchannels/{self._index}/sines/0/oscselect")
        return f"sgchannels/{self._index}/oscs/{selected_osc}/freq"

    def _init_awg_params(self):
        self._enable = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/awg/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.output1 = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/outputs/0/enables"
            ),
            device=self._parent,
            get_parser=Parse.get_on_off,
        )
        self.output2 = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/outputs/1/enables"
            ),
            device=self._parent,
            get_parser=Parse.get_on_off,
        )
        self.modulation_freq = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/oscs/0/freq"),
            device=self._parent,
            dynamic_path=lambda v: v._get_modulation_freq_node(),
            set_parser=lambda v: Parse.greater(v, 0),
        )
        self.modulation_phase_shift = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/sines/0/phaseshift"),
            device=self._parent,
            set_parser=Parse.phase,
        )
        self.gain00 = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/outputs/0/gains/0"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.gain01 = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/outputs/0/gains/1"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.gain10 = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/outputs/1/gains/0"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.gain11 = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/outputs/1/gains/1"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.single = Parameter(
            self,
            self._parent._get_node_dict(f"sgchannels/{self._index}/awg/single"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )

        self.digital_trigger1_source = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/auxtriggers/0/channel"
            ),
            device=self._parent,
            auto_mapping=True,
        )

        self.digital_trigger2_source = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/auxtriggers/1/channel"
            ),
            device=self._parent,
            auto_mapping=True,
        )
        self.digital_trigger1_slope = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/auxtriggers/0/slope"
            ),
            device=self._parent,
            auto_mapping=True,
        )

        self.digital_trigger2_slope = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/awg/auxtriggers/1/slope"
            ),
            device=self._parent,
            auto_mapping=True,
        )

        self.osc_select = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._index}/sines/0/oscselect"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 0),
                lambda v: Parse.smaller_equal(v, 7),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        )

        # TODO Right now not available/needed on the shfsg
        # self.zsync_register_mask = Parameter(
        #     self,
        #     self._parent._get_node_dict(f"awgs/{self._index}/zsync/register/mask"),
        #     device=self._parent,
        #     set_parser=[
        #         lambda v: Parse.smaller_equal(v, 15),
        #         lambda v: Parse.greater_equal(v, 0),
        #     ],
        # )
        # self.zsync_register_shift = Parameter(
        #     self,
        #     self._parent._get_node_dict(f"awgs/{self._index}/zsync/register/shift"),
        #     device=self._parent,
        #     set_parser=[
        #         lambda v: Parse.smaller_equal(v, 3),
        #         lambda v: Parse.greater_equal(v, 0),
        #     ],
        # )
        # self.zsync_register_offset = Parameter(
        #     self,
        #     self._parent._get_node_dict(f"awgs/{self._index}/zsync/register/offset"),
        #     device=self._parent,
        #     set_parser=[
        #         lambda v: Parse.smaller_equal(v, 1023),
        #         lambda v: Parse.greater_equal(v, 0),
        #     ],
        # )
        # self.zsync_decoder_mask = Parameter(
        #     self,
        #     self._parent._get_node_dict(f"awgs/{self._index}/zsync/decoder/mask"),
        #     device=self._parent,
        #     set_parser=[
        #         lambda v: Parse.smaller_equal(v, 255),
        #         lambda v: Parse.greater_equal(v, 0),
        #     ],
        # )
        # self.zsync_decoder_shift = Parameter(
        #     self,
        #     self._parent._get_node_dict(f"awgs/{self._index}/zsync/decoder/shift"),
        #     device=self._parent,
        #     set_parser=[
        #         lambda v: Parse.smaller_equal(v, 7),
        #         lambda v: Parse.greater_equal(v, 0),
        #     ],
        # )
        # self.zsync_decoder_offset = Parameter(
        #     self,
        #     self._parent._get_node_dict(f"awgs/{self._index}/zsync/decoder/offset"),
        #     device=self._parent,
        #     set_parser=[
        #         lambda v: Parse.smaller_equal(v, 1023),
        #         lambda v: Parse.greater_equal(v, 0),
        #     ],
        # )

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
        self._parent._set(f"sgchannels/{i}/awg/modulation/enable", 1)
        self.set_sequence_params(reset_phase=True)
        # TODO Right now not available/needed on the shfsg
        # self._parent._set("system/awg/oscillatorcontrol", 1)

    def disable_iq_modulation(self) -> None:
        """Disables IQ modulation on the AWG Core.

        Resets the settings of the sine generators and the AWG modulation.

        """
        self._iq_modulation = False
        i = self._index
        self._parent._set(f"sgchannels/{i}/awg/modulation/enable", 0)
        self.set_sequence_params(reset_phase=False)
        # TODO Right now not available/needed on the shfsg
        # self._parent._set("system/awg/oscillatorcontrol", 0)

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
        self._parent._set(f"sgchannels/{i}/awg/auxtriggers/*/channel", 2 * i)
        self._parent._set(f"sgchannels/{i}/awg/auxtriggers/*/slope", 1)  # rise

    def _apply_zsync_trigger_settings(self):
        pass
        # i = self._index
        # settings = [
        #     # Configure DIO trigger
        #     # Set signal edge of the STROBE signal to off
        #     (f"/awgs/{i}/dio/strobe/slope", "off"),
        #     # Ignore VALID bit, trigger on any valid input
        #     (f"/awgs/{i}/dio/valid/polarity", "none"),
        # ]
        # self._parent._set(settings)

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

    @property
    def ct(self):
        return self._ct


class Sine:
    """Sine Channel for a SG Channel of the SHFSG.
    This class pepresents a single sine channel for the SHFSG.
    It offers functionality to control the sine specific node.

    Attributes:
        osc_select (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Selected oscillator for the sine generation.
        harmonic (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Harmonic.
        phase_shift (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Phase shift.
        i_enable (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Enable I Channel for the Sine generation.
        i_sin (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Amplitude for the sine in the I Channel.
        i_cos (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Amplitude for the cosine in the I Channel.
        q_enable (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Enable Q Channel for the Sine generation.
        q_sin (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Amplitude for the sine in the Q Channel.
        q_cos (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Amplitude for the cosine in the Q Channel.
    """
    def __init__(self, parent: BaseInstrument, parent_index: int, index: int) -> None:
        self._parent = parent
        self._parent_index = parent_index
        self._index = index

    def _setup(self):

        self.osc_select = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/oscselect"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 0),
                lambda v: Parse.smaller_equal(v, 7),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        )
        self.harmonic = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/harmonic"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 1),
                lambda v: Parse.smaller_equal(v, 1023),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        )
        # self.freq = Parameter(
        #     self,
        #     self._parent._get_node_dict(
        #         f"sgchannels/{self._parent_index}/sines/{self._index}/freq"
        #     ),
        #     device=self._parent,
        # )
        self.phase_shift = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/phaseshift"
            ),
            device=self._parent,
            set_parser=lambda v: Parse.greater_equal(v, 0),
        )
        self.i_enable = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/i/enable"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 0),
                lambda v: Parse.smaller_equal(v, 1),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        )
        self.i_sin = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/i/sin/amplitude"
            ),
            device=self._parent,
            set_parser=lambda v: Parse.greater_equal(v, 0),
        )
        self.i_cos = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/i/cos/amplitude"
            ),
            device=self._parent,
            set_parser=lambda v: Parse.greater_equal(v, 0),
        )
        self.q_enable = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/q/enable"
            ),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 0),
                lambda v: Parse.smaller_equal(v, 1),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        )
        self.q_sin = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/q/sin/amplitude"
            ),
            device=self._parent,
            set_parser=lambda v: Parse.greater_equal(v, 0),
        )
        self.q_cos = Parameter(
            self,
            self._parent._get_node_dict(
                f"sgchannels/{self._parent_index}/sines/{self._index}/q/cos/amplitude"
            ),
            device=self._parent,
            set_parser=lambda v: Parse.greater_equal(v, 0),
        )
