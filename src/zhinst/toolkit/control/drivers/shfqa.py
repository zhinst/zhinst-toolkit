# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import logging
import time

from zhinst.toolkit.control.drivers.base import (
    BaseInstrument,
    SHFChannel,
    SHFGenerator,
    SHFScope,
    SHFSweeper,
)
from zhinst.toolkit.interface import DeviceTypes
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse

_logger = logging.getLogger(__name__)


class SHFQA(BaseInstrument):
    """High-level driver for the Zurich Instruments SHFQA Quantum Analyzer.

    Inherits from :class:`BaseInstrument` and defines device specific
    methods and properties. All Channels of the :class:`SHFQA` can be
    accessed through the property `channels` that is a list of four
    :class:`Channel` s that are specific for the device and inherit from
    the :class:`SHFChannel` class. All Generators of the :class:`SHFQA`
    can be accessed through the property `generators` that is a list of
    four :class:`Generator` s that are specific for the device and
    inherit from the :class:`SHFGenerator` class.

    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.SHFQA, serial, discovery, **kwargs)
        self._channels = []
        self._scope = None
        self.ref_clock = None
        self.ref_clock_actual = None
        self.ref_clock_status = None
        self.timebase = None

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server.

        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from
                the device's nodetree should be added to the object's attributes
                as `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)
        self._init_channels()
        self._init_scope()

    def factory_reset(self) -> None:
        """Loads the factory default settings."""
        _logger.info(f"Factory preset is not supported in {self.serial.upper()}.")

    def _init_settings(self):
        """Sets initial device settings on startup."""
        pass

    def _num_channels(self):
        """Find the number of channels available in the instrument."""
        serial = self.serial
        daq = self._controller._connection._daq
        channels = daq.listNodes(f"{serial}/qachannels/")
        num_channels = len(channels)
        return num_channels

    def _init_channels(self):
        """Initialize the channels of the device."""
        self._channels = [Channel(self, i) for i in range(self._num_channels())]
        [channel._init_channel_params() for channel in self.channels]
        [channel._init_generator() for channel in self.channels]
        [channel._init_sweeper() for channel in self.channels]

    def _init_scope(self):
        """Initialize the scope of the device."""
        self._scope = Scope(self)
        self._scope._init_scope_params()

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        super()._init_params()
        self.ref_clock = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/source"),
            device=self,
            auto_mapping=True,
        )
        self.ref_clock_actual = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/sourceactual"),
            device=self,
            auto_mapping=True,
        )
        self.ref_clock_status = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/status"),
            device=self,
            get_parser=Parse.get_locked_status,
        )
        self.timebase = Parameter(
            self,
            self._get_node_dict(f"system/properties/timebase"),
            device=self,
        )

    def set_trigger_loopback(self):
        """Start a trigger pulse using the internal loopback.

        Start a 1kHz continuous trigger pulse from marker 1 A using the
        internal loopback to trigger in 1 A.
        """

        m_ch = 0
        continuous_trig = 1
        self._set(f"/raw/markers/{m_ch}/testsource", continuous_trig)
        self._set(f"/raw/markers/{m_ch}/frequency", 1e3)
        self._set(f"/raw/triggers/{m_ch}/loopback", 1)
        time.sleep(0.2)

    @property
    def channels(self):
        return self._channels

    @property
    def scope(self):
        return self._scope


class Channel(SHFChannel):
    """Device-specific Channel for SHFQA.

    This class inherits from the base :class:`SHFChannel` and adds
    :mod:`zhinst-toolkit` :class:`Parameters` such as output, input or
    center frequency.

    Attributes:
        generator (:class:`zhinst.toolkit.control.drivers.shfqa.Generator`):
            A device-specific :class:`SHFGenerator` for the SHFQA.
        sweeper (:class:`zhinst.toolkit.control.drivers.shfqa.Sweeper`):
            A device-specific :class:`SHFSweeper` for the SHFQA.
        input (:class:`Parameter`): State of the input, i.e. one of
            {'on', 'off'}.
        input_range (:class:`Parameter`): Maximal range in dBm of the
            signal input power. The instrument selects the closest
            available range with a resolution of 5 dBm.
        output (:class:`Parameter`): State of the output, i.e. one of
            {'on', 'off'}.
        output_range (:class:`Parameter`): Maximal range in dBm of the
            signal input power. The instrument selects the closest
            available range with a resolution of 5 dBm.
        center_freq (:class:`Parameter`): The center frequency in Hz of
            the analysis band
        mode (:class:`Parameter`): Select between `"Spectroscopy"` and
            `"Qubit Readout"` mode
            `"Spectroscopy"`: the Signal Output is connected to the
            Oscillator, with which also the measured signals are
            correlated.',.
            `"Qubit Readout"`: the Signal Output is connected to the
            Readout Pulse Generator, and the measured signals are
            correlated with the Integration Weights before state
            discrimination.

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        super().__init__(parent, index)
        self._generator = []
        self._sweeper = []
        self.input = None
        self.input_range = None
        self.output = None
        self.output_range = None
        self.center_freq = None
        self.mode = None

    def _init_channel_params(self):
        self.input = Parameter(
            self,
            self._parent._get_node_dict(f"qachannels/{self._index}/input/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.input_range = Parameter(
            self,
            self._parent._get_node_dict(f"qachannels/{self._index}/input/range"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, -50),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        )
        self.output = Parameter(
            self,
            self._parent._get_node_dict(f"qachannels/{self._index}/output/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.output_range = Parameter(
            self,
            self._parent._get_node_dict(f"qachannels/{self._index}/output/range"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, -50),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        )
        self.center_freq = Parameter(
            self,
            self._parent._get_node_dict(f"qachannels/{self._index}/centerfreq"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 1e9),
                lambda v: Parse.smaller_equal(v, 8e9),
                lambda v: Parse.multiple_of(v, 100e6, "nearest"),
            ],
        )
        self.mode = Parameter(
            self,
            self._parent._get_node_dict(f"qachannels/{self._index}/mode"),
            device=self._parent,
            auto_mapping=True,
        )

    def _init_generator(self):
        """Initialize the genereator of the channel."""
        self._generator = Generator(self)
        self._generator._setup()
        self._generator._init_generator_params()

    def _init_sweeper(self):
        """Initialize the sweeper of the channel."""
        self._sweeper = Sweeper(self)
        self._sweeper._init_sweeper_params()

    @property
    def generator(self):
        return self._generator

    @property
    def sweeper(self):
        return self._sweeper


class Generator(SHFGenerator):
    """Device-specific Generator for SHFQA.

    This class inherits from the base :class:`SHFGenerator`.
    """

    def __init__(self, parent: SHFChannel) -> None:
        super().__init__(parent)
        self.enable = None
        self.dig_trigger1_source = None
        self.dig_trigger2_source = None
        self.ready = None

    def _init_generator_params(self):
        self.enable = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/generator/sequencer/enable"
            ),
            device=self._device,
        )
        self.dig_trigger1_source = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/generator/sequencer/auxtriggers/0/channel"
            ),
            device=self._device,
            auto_mapping=True,
        )
        self.dig_trigger2_source = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/generator/sequencer/auxtriggers/1/channel"
            ),
            device=self._device,
            auto_mapping=True,
        )
        self.ready = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/generator/sequencer/ready"
            ),
            device=self._device,
        )


class Sweeper(SHFSweeper):
    """Device-specific Sweeper for SHFQA.

    This class inherits from the base :class:`SHFSweeper`.
    """

    def __init__(self, parent: SHFChannel) -> None:
        super().__init__(parent)
        self._trigger_source = "sw_trigger"
        self._trigger_level = 0.5
        self._trigger_imp50 = True
        self._start_freq = -300e6
        self._stop_freq = 300e6
        self._num_points = 100
        self._mapping = "linear"
        self.oscillator_gain = None
        self.integration_time = None
        self.integration_length = None
        self._num_averages = 1
        self._averaging_mode = "sweepwise"

    def _init_sweeper_params(self):
        self.oscillator_gain = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/oscs/0/gain"),
            device=self._device,
            set_parser=lambda v: v
            if v in [Parse.smaller_equal(v, 1.0), Parse.greater_equal(v, 0.01)]
            else None,
        )
        self.integration_time = Parameter(
            self,
            dict(
                Node=f"{self._device.serial}/qachannels/{self._index}/spectroscopy/length".upper(),
                Description="Sets the integration length in Spectroscopy mode in unit "
                "of seconds. Up to 16.7 ms can be recorded, which "
                "corresponds to 33.5 MSa (2^25 samples).",
                Type="Double",
                Properties="Read, Write, Setting",
                Unit="s",
            ),
            device=self._device,
            set_parser=Parse.shfqa_time2samples,
            get_parser=Parse.shfqa_samples2time,
        )
        self.integration_length = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/spectroscopy/length"
            ),
            device=self._device,
            set_parser=[
                lambda v: Parse.greater_equal(v, 4),
                lambda v: Parse.smaller_equal(v, ((2 ** 23) - 1) * 4),
                lambda v: Parse.multiple_of(v, 4, "down"),
            ],
        )

    def trigger_source(self, source=None):
        """Set or get the trigger source for the sweeper.

        Keyword Arguments:
            source (str): Trigger source of the sweeper
                (default: None).

        """
        if source is None:
            return self._trigger_source
        else:
            self._trigger_source = source
        self._update_trigger_settings()

    def trigger_level(self, level=None):
        """Set or get the trigger level for the sweeper.

        Keyword Arguments:
            level (float): Trigger level of the sweeper
                (default: None).

        """
        if level is None:
            return self._trigger_level
        else:
            self._trigger_level = level
        self._update_trigger_settings()

    def trigger_imp50(self, imp50=None):
        """Set or get the trigger input impedance setting for the sweeper.

        Keyword Arguments:
            imp50 (bool): Trigger input impedance selection for the
                sweeper. When set to True, the trigger input impedance is
                50 Ohm. When set to False, it is 1 kOhm (default: None).

        """
        if imp50 is None:
            return self._trigger_imp50
        else:
            self._trigger_imp50 = imp50
        self._update_trigger_settings()

    def start_frequency(self, freq=None):
        """Set or get the start frequency for the sweeper.

        Keyword Arguments:
            freq (float): Start frequency in Hz of the sweeper
                (default: None).

        """
        if freq is None:
            return self._start_freq
        else:
            self._start_freq = freq
        self._update_sweep_params()

    def stop_frequency(self, freq=None):
        """Set or get the stop frequency for the sweeper.

        Keyword Arguments:
            freq (float): Stop frequency in Hz of the sweeper
                (default: None).

        """
        if freq is None:
            return self._stop_freq
        else:
            self._stop_freq = freq
        self._update_sweep_params()

    def num_points(self, num=None):
        """Set or get the number of points for the sweeper.

        Keyword Arguments:
            num (int): Number of frequency points to sweep between
                start and stop frequency values (default: None).
        """
        if num is None:
            return self._num_points
        else:
            self._num_points = num
        self._update_sweep_params()

    def mapping(self, map=None):
        """Set or get the mapping configuration for the sweeper.

        Keyword Arguments:
            map (str): Mapping that specifies the distances between
                frequency points of the sweeper. Can be either "linear"
                or "log" (default: None).
        """
        if map is None:
            return self._mapping
        else:
            self._mapping = map
        self._update_sweep_params()

    def num_averages(self, num=None):
        """Set or get the number of averages for the sweeper.

        Number of averages specifies how many times a frequency point
        will be measured and averaged.

        Keyword Arguments:
            num (int): Number of times the sweeper measures one
                frequency point (default: None).
        """
        if num is None:
            return self._num_averages
        else:
            self._num_averages = num
        self._update_averaging_settings()

    def averaging_mode(self, mode=None):
        """Set or get the averaging mode for the sweeper.

        Keyword Arguments:
            mode (str): Averaging mode for the sweeper.
        Can be either "sequantial" or "cyclic".
            "sequential": A frequency point is measured the number of
                times specified by the number of samples setting. In
                other words, the same frequency point is measured
                repeatedly until the number of samples is reached and
                the sweeper then moves to the next frequency point.
            "cyclic": All frequency points are measured once from
                start frequency to stop frequency. The sweeper then
                moves back to start frequency and repeats the sweep
                the number of times specified by the number of samples
                setting.
            (default: None).
        """
        if mode is None:
            if self._averaging_mode == "pointwise":
                return "sequantial"
            elif self._averaging_mode == "sweepwise":
                return "cyclic"
            else:
                return self._averaging_mode
        else:
            if mode == "sequential":
                self._averaging_mode = "pointwise"
            elif mode == "cyclic":
                self._averaging_mode = "sweepwise"
            else:
                self._averaging_mode = mode
        self._update_averaging_settings()


class Scope(SHFScope):
    """Device-specific Scope for SHFQA.

    This class inherits from the base :class:`SHFScope`.
    """

    def __init__(self, parent: BaseInstrument) -> None:
        super().__init__(parent)
        self.enable = None
        self.channel1 = None
        self.channel2 = None
        self.channel3 = None
        self.channel4 = None
        self.input_select1 = None
        self.input_select2 = None
        self.input_select3 = None
        self.input_select4 = None
        self.wave1 = None
        self.wave2 = None
        self.wave3 = None
        self.wave4 = None
        self.trigger_source = None
        self.trigger_delay = None
        self.length = None
        self.time = None
        self.segments_enable = None
        self.segments_count = None
        self.averaging_enable = None
        self.averaging_count = None

    def _init_scope_params(self):
        self.enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/enable"),
            device=self._parent,
        )
        self.channel1 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/0/enable"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.channel2 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/1/enable"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.channel3 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/2/enable"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.channel4 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/3/enable"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.input_select1 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/0/inputselect"),
            device=self._parent,
        )
        self.input_select2 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/1/inputselect"),
            device=self._parent,
        )
        self.input_select3 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/2/inputselect"),
            device=self._parent,
        )
        self.input_select4 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/3/inputselect"),
            device=self._parent,
        )
        self.wave1 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/0/wave"),
            device=self._parent,
        )
        self.wave2 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/1/wave"),
            device=self._parent,
        )
        self.wave3 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/2/wave"),
            device=self._parent,
        )
        self.wave4 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/3/wave"),
            device=self._parent,
        )
        self.trigger_source = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigger/channel"),
            device=self._parent,
        )
        self.trigger_delay = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigger/delay"),
            device=self._parent,
            set_parser=lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        )
        self.length = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/length"),
            device=self._parent,
            set_parser=lambda v: Parse.multiple_of(v, 32, "nearest"),
        )
        self.time = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/time"),
            device=self._parent,
            auto_mapping=True,
        )
        self.segments_enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/segments/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.segments_count = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/segments/count"),
            device=self._parent,
            set_parser=lambda v: Parse.greater(v, 0),
        )
        self.averaging_enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/averaging/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.averaging_count = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/averaging/count"),
            device=self._parent,
            set_parser=lambda v: Parse.greater(v, 0),
        )
