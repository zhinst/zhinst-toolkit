# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import time

from zhinst.toolkit.control.drivers.base import (
    BaseInstrument,
    SHFQAChannel,
    SHFGenerator,
    SHFReadout,
    SHFIntegration,
    SHFScope,
    SHFSweeper,
)
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.helpers import SequenceType, TriggerMode

_logger = LoggerModule(__name__)


class SHFQA(BaseInstrument):
    """High-level driver for the Zurich Instruments SHFQA Quantum Analyzer.

    Inherits from :class:`BaseInstrument` and defines device specific
    methods and properties. All QAChannels of the :class:`SHFQA` can be
    accessed through the property `qachannels` that is a list of four
    :class:`QAChannel` s that are specific for the device and inherit from
    the :class:`SHFQAChannel` class. Similarly, the Scope of the
    :class:`SHFQA` can be accessed through the property `scope`

        >>> from zhinst.toolkit import SHFQA
        >>> ...
        >>> shf = SHFQA("shfqa 1", "dev12000")
        >>> shf.setup()
        >>> shf.connect_device()
        >>> shf.nodetree
        <zhinst.toolkit.control.node_tree.NodeTree object at 0x00000224288A97C8>
        nodes:
         - stats
         - status
         - system
         - features
         - qachannels
         - scope
         - dio
        parameters:
         - clockbase


    Arguments:
        name (str): Identifier for the SHFQA.
        serial (str): Serial number of the device, e.g. *'dev12000'*.
            The serial number can be found on the back panel of the
            instrument.
        discovery: an instance of ziDiscovery

    Attributes:
        qachannels (list): A list of four device-specific SHFQAChannels
            of type :class:`zhinst.toolkit.control.drivers.shfqa.QAChannel`.
        scope (:class:`zhinst.toolkit.control.drivers.shfqa.Scope`):
            A device-specific SHFScope.
        allowed_sequences (list): A list of :class:`SequenceType` s
            that the instrument supports.
        allowed_trigger_modes (list): A list of :class:`TriggerMode` s
            that the instrument supports.
        sw_trigger (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Issues a single software trigger event
        ref_clock (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The intended reference clock source to be used as the
            frequency and time base reference. When the source is
            changed, all the instruments connected with ZSync links will
            be disconnected. The connection should be re-established
            manually. Can be either `0: "internal"` or `1: "external"`.\n
            `0: "internal"`: Internal 10 MHz clock\n
            `1: "external"`: An external clock. Provide a clean and stable
            10 MHz or 100 MHz reference to the appropriate back panel
            connector.
        ref_clock_actual (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The actual reference clock source. Can be either `0: "internal"`
            or `1: "external"`.\n
            `0: "internal"`: Internal 10 MHz clock\n
            `1: "external"`: An external clock.
        ref_clock_status (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Status of the reference clock. Can be either `0: "locked"`,
            `1: "error"` or `2: "busy"`.
    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.SHFQA, serial, discovery, **kwargs)
        self._qachannels = []
        self._scope = None
        self.sw_trigger = None
        self.ref_clock = None
        self.ref_clock_actual = None
        self.ref_clock_status = None
        self._allowed_sequences = [
            SequenceType.NONE,
            SequenceType.CUSTOM,
        ]
        self._allowed_trigger_modes = [
            TriggerMode.NONE,
            TriggerMode.RECEIVE_TRIGGER,
            TriggerMode.ZSYNC_TRIGGER,
        ]

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server.

        Arguments:
            nodetree (bool): A flag that specifies if all the parameters from
                the device's nodetree should be added to the object's attributes
                as `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)
        self._init_qachannels()
        self._init_scope()

    def factory_reset(self, sync=True) -> None:
        """Load the factory default settings.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).
        """
        _logger.warning(
            f"Factory preset is not yet supported in SHFQA " f"{self.serial.upper()}."
        )

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

    def _init_settings(self):
        """Sets initial device settings on startup."""
        pass

    def num_qachannels(self):
        """Find the number of qachannels available in the instrument."""
        serial = self.serial
        daq = self._controller.connection.daq
        qachannels = daq.listNodes(f"{serial}/qachannels/")
        return len(qachannels)

    def num_integrations_per_qachannel(self):
        """Find the number of integration units per qachannel."""
        serial = self.serial
        daq = self._controller.connection.daq
        integrations = daq.listNodes(f"{serial}/qachannels/0/readout/discriminators")
        return len(integrations)

    def _init_qachannels(self):
        """Initialize the qachannels of the device."""
        self._qachannels = [QAChannel(self, i) for i in range(self.num_qachannels())]
        [qachannel._init_qachannel_params() for qachannel in self.qachannels]
        [qachannel._init_generator() for qachannel in self.qachannels]
        [qachannel._init_readout() for qachannel in self.qachannels]
        [qachannel._init_sweeper() for qachannel in self.qachannels]

    def _init_scope(self):
        """Initialize the scope of the device."""
        self._scope = Scope(self)
        self._scope._init_scope_params()

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        super()._init_params()
        self.sw_trigger = Parameter(
            self,
            self._get_node_dict(f"system/swtriggers/0/single"),
            device=self,
        )
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

    def set_trigger_loopback(self):
        """Start a trigger pulse using the internal loopback.

        A 1kHz continuous trigger pulse from marker 1 A using the
        internal loopback to trigger in 1 A.
        """

        m_ch = 0
        low_trig = 2
        continuous_trig = 1
        self._set(f"/raw/markers/*/testsource", low_trig, sync=True)
        self._set(f"/raw/markers/{m_ch}/testsource", continuous_trig)
        self._set(f"/raw/markers/{m_ch}/frequency", 1e3)
        self._set(f"/raw/triggers/{m_ch}/loopback", 1)
        time.sleep(0.2)

    def clear_trigger_loopback(self):
        """Stop the the internal loopback trigger pulse."""
        m_ch = 0
        self._set(f"/raw/markers/*/testsource", 0)
        self._set(f"/raw/triggers/{m_ch}/loopback", 0)

    @property
    def qachannels(self):
        return self._qachannels

    @property
    def scope(self):
        return self._scope

    @property
    def allowed_sequences(self):
        return self._allowed_sequences

    @property
    def allowed_trigger_modes(self):
        return self._allowed_trigger_modes


class QAChannel(SHFQAChannel):
    """Device-specific QAChannel for SHFQA.

    This class inherits from the base :class:`SHFQAChannel` and adds
    :mod:`zhinst-toolkit` :class:`Parameter` s such as output, input or
    center frequency. The Generator of a :class:`QAChannel` can be
    accessed through the property `generator` which is a
    :class:`Generator` specific for the device and inherits from the
    :class:`SHFGenerator` class. The Sweeper of a :class:`QAChannel`
    can be accessed through the property `sweeper` that is a
    :class:`Sweeper` specific for the device and inherits from the
    :class:`SHFSweeper` class.

    See more about SHF QAChannels at
    :class:`zhinst.toolkit.control.drivers.base.SHFQAChannel`.

    Attributes:
        generator (:class:`zhinst.toolkit.control.drivers.shfqa.Generator`):
            A device-specific :class:`SHFGenerator` for the SHFQA.
        readout (:class:`zhinst.toolkit.control.drivers.shfqa.Readout`):
            A device-specific :class:`SHFReadout` for the SHFQA.
        sweeper (:class:`zhinst.toolkit.control.drivers.shfqa.Sweeper`):
            A device-specific :class:`SHFSweeper` for the SHFQA.
        input (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the input, i.e. one of {'on', 'off'}.
        input_range (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Maximal range in dBm of the signal input power. The
            instrument selects the closest available range with a
            resolution of 5 dBm.
        output (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the output, i.e. one of {'on', 'off'}.
        output_range (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Maximal range in dBm of the signal input power. The
            instrument selects the closest available range with a
            resolution of 5 dBm.
        center_freq (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The center frequency in Hz of the analysis band. Must be
            between 1 GHz and 8 GHz.
        mode (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select between Spectroscopy and Qubit Readout modes\n
            `"spectroscopy"`: the Signal Output is connected to the
            Oscillator, with which also the measured signals are
            correlated.\n
            `"readout"`: the Signal Output is connected to the
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

    def _init_qachannel_params(self):
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
        """Initialize the generator of the qachannel."""
        self._generator = Generator(self)
        self._generator._setup()
        self._generator._init_generator_params()

    def _init_readout(self):
        """Initialize the readout module of the qachannel."""
        self._readout = Readout(self)
        self._readout._init_readout_params()
        self._readout._init_integrations()

    def _init_sweeper(self):
        """Initialize the sweeper of the qachannel."""
        self._sweeper = Sweeper(self)
        self._sweeper._init_sweeper_params()

    @property
    def generator(self):
        return self._generator

    @property
    def readout(self):
        return self._readout

    @property
    def sweeper(self):
        return self._sweeper


class Generator(SHFGenerator):
    """Device-specific Generator for SHFQA.

    This class inherits from the base :class:`SHFGenerator` and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s such as digital trigger
    sources or single. It also applies sequence specific settings for
    the SHFQA, depending on the type of :class:`SequenceProgram` on the
    SHF Generator.

        >>> shf.qachannels[0].generator
        <zhinst.toolkit.control.drivers.shfqa.Generator object at 0x0000017E57BEEE48>
            parent  : <zhinst.toolkit.control.drivers.shfqa.QAChannel object at 0x0000017E57BE9748>
            index   : 0
            sequence:
                type: SequenceType.NONE
                ('target', <DeviceTypes.SHFQA: 'shfqa'>)
                ('clock_rate', 2000000000.0)
                ('period', 0.0001)
                ('trigger_mode', <TriggerMode.SEND_TRIGGER: 'Send Trigger'>)
                ('trigger_samples', 32)
                ('repetitions', 1)
                ('alignment', <Alignment.END_WITH_TRIGGER: 'End with Trigger'>)
                ...

        >>> shf.qachannels[0].output('on')
        >>> shf.qachannels[0].output_range(10)
        >>> shf.qachannels[0].generator.single(True)
        >>> shf.qachannels[0].generator.dig_trigger1_source('chan0trigin0')
        'chan0trigin0'

    See more about SHFGenerators at
    :class:`zhinst.toolkit.control.drivers.base.SHFGenerator`.

    Attributes:
        single (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the Generator single shot mode, i.e. one of
            {True, False} (default: True).
        dig_trigger1_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Selects the source of the Digital Trigger 1
            (default: 'chan0trigin0').\n
            To list the available options: \n
            >>> shf.qachannels[0].generator.dig_trigger1_source
        dig_trigger2_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Selects the source of the Digital Trigger 2
            (default: 'chan0trigin0'). \n
            To list the available options: \n
            >>> shf.qachannels[0].generator.dig_trigger2_source
        playback_delay (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            A common delay for the start of the playback for all
            Waveform Memories. The resolution is 2 ns (default: 0.0).
    """

    def __init__(self, parent: SHFQAChannel) -> None:
        super().__init__(parent)
        self._enable = None
        self.dig_trigger1_source = None
        self.dig_trigger2_source = None
        self.playback_delay = None
        self._ready = None
        self.single = None

    def _init_generator_params(self):
        self._enable = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/generator/enable"),
            device=self._device,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.dig_trigger1_source = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/generator/auxtriggers/0/channel"
            ),
            device=self._device,
            auto_mapping=True,
        )
        self.dig_trigger2_source = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/generator/auxtriggers/1/channel"
            ),
            device=self._device,
            auto_mapping=True,
        )
        self.playback_delay = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/generator/delay"),
            device=self._device,
            set_parser=lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        )
        self._ready = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/generator/ready"),
            device=self._device,
        )
        self.single = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/generator/single"),
            device=self._device,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )

    def _apply_sequence_settings(self, **kwargs) -> None:
        super()._apply_sequence_settings(**kwargs)


class Readout(SHFReadout):
    """Device-specific Readout module for SHFQA.

    This class inherits from the base :class:`SHFReadout` and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s such as integration
    length or result source.

    See more about SHFReadout modules at
    :class:`zhinst.toolkit.control.drivers.base.SHFReadout`.

    Attributes:
        integration_length (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The integration length in number of samples. The value
            must be greater than and multiple of 4. A maximum of 4096
            samples can be integrated, which corresponds to 2.05 us.
            (default: 128).
        integration_delay (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The integration length in number of samples. The value
            must be greater than and multiple of 4. A maximum of 4096
            samples can be integrated, which corresponds to 2.05 us.
            (default: 128).
        result_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            This parameter selects the stage in the signal processing
            path that is used as the source for the QA results. It can
            be one of {`"Crosstalk"`, `"Threshold"`, `"Rotation"`,
            `"Crosstalk Correlation"`, `"Threshold Correlation"`,
            `"Integration"`}.
        result_length (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Number of data points to record. One data point corresponds
            to a single averaged result value of the selected source
            (default: 1).
        num_averages (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Number of measurements that are averaged. Only powers of 2
            are valid, other values are rounded down to the next power
            of 2. 1 means no averaging. The maximum setting is 32768.
            (default: 1).

    """

    def __init__(self, parent: SHFQAChannel) -> None:
        super().__init__(parent)
        self._integrations = []
        self._enable = None
        self.integration_length = None
        self.integration_delay = None
        self.result_source = None
        self.result_length = None
        self.num_averages = None

    def _init_readout_params(self):
        self._enable = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/readout/result/enable"
            ),
            device=self._device,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.integration_length = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/readout/integration/length"
            ),
            device=self._device,
        )
        self.integration_delay = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/readout/integration/delay"
            ),
            device=self._device,
        )
        self.result_source = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/readout/result/source"
            ),
            device=self._device,
            auto_mapping=True,
        )
        self.result_length = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/readout/result/length"
            ),
            device=self._device,
        )
        self.num_averages = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/readout/result/averages"
            ),
            device=self._device,
        )

    def _init_integrations(self):
        """Initialize the integration units of the readout module."""
        self._integrations = [
            Integration(self, i)
            for i in range(self._device.num_integrations_per_qachannel())
        ]
        [integration._init_integration_params() for integration in self._integrations]

    @property
    def integrations(self):
        return self._integrations


class Integration(SHFIntegration):
    """Implements an integration for the SHFQA.

    This class represents the signal processing chain for one of the
    :class:`Integration`s of the SHFQA. Integration is typically used
    for dispersive resonator readout of superconducting qubits.

    Attributes:
        index (int): The index of the Integration.
        threshold (:class:`zhinst.toolkit.control.nodetree.Parameter`):
            The signal threshold used for state discrimination in the
            thresholding unit.
        result (:class:`zhinst.toolkit.control.nodetree.Parameter`):
            This read-only Parameter holds the result vector data for
            the given integration. Depending on the source of the data,
            the data can be complex- or integer-valued.
        weights (:class:`zhinst.toolkit.control.nodetree.Parameter`):
            Contains the complex-valued waveform of the Integration
            Weight. The valid range is between -1.0 and +1.0 for both
            the real and imaginary part.

    """

    def __init__(self, parent: SHFReadout, index: int) -> None:
        super().__init__(parent, index)
        self.threshold = None
        self.result = None
        self.weights = None

    def _init_integration_params(self):
        self.threshold = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._parent_index}"
                f"/readout/discriminators/{self._index}/threshold"
            ),
            device=self._device,
        )
        self.result = Parameter(
            self,
            self._device._get_node_dict(
                f"/qachannels/{self._parent_index}"
                f"/readout/result/data/{self._index}/wave"
            ),
            device=self._device,
        )
        self.weights = Parameter(
            self,
            self._device._get_node_dict(
                f"/qachannels/{self._parent_index}"
                f"/readout/integration/weights/{self._index}/wave"
            ),
            device=self._device,
        )


class Sweeper(SHFSweeper):
    """Device-specific Sweeper for SHFQA.

    This class inherits from the base :class:`SHFSweeper` and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s such as integration time
    or oscillator_gain.

    A typical sweeper configuration for a simple spectroscopy
    measurement would look like this:

        >>> sweeper = shf.qachannels[0].sweeper
        >>> # Trigger settings
        >>> sweeper.trigger_source("channel0_trigger_input0")
        >>> sweeper.trigger_level(0)
        >>> sweeper.trigger_imp50(1)
        >>> # Sweep settings
        >>> sweeper.oscillator_gain(0.8)
        >>> sweeper.start_frequency(0)
        >>> sweeper.stop_frequency(200e6)
        >>> sweeper.num_points(51)
        >>> sweeper.mapping("linear")
        >>> # Averaging settings
        >>> sweeper.integration_time(100e-6)
        >>> sweeper.num_averages(2)
        >>> sweeper.averaging_mode("sequential")

    See more about SHF Sweepers at
    :class:`zhinst.toolkit.control.drivers.base.SHFSweeper`.

    Attributes:
        integration_time (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Integration length in Spectroscopy mode in unit of seconds.
            Note that setting the `integration_time` automatically
            updates the `integration_length`. The integration time has
            a minimum value and a granularity of 2 ns. Up to 16.7 ms can
            be recorded (default: 512e-9).
        integration_length (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Integration length in Spectroscopy mode in number of samples.
            Note that setting the `integration_length` automatically
            updates the `integration_time`. The integration length has
            a minimum value and a granularity of 4 samples. Up to
            33.5 MSa (2^25 samples) can be recorded (default: 1024).
        integration_delay (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Sets the delay of the integration in Spectroscopy mode with
            respect to the Trigger signal. The resolution is 2 ns
            (default: 0).
        oscillator_gain (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the digital Oscillator. The gain is defined relative
            to the Output Range of the QAChannel. Must be between 0
            and 1.0 (default: 1.0).
        oscillator_freq (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Controls the frequency of each digital Oscillator. Must be
            between 0 and 1e9 (default: 10e6).
        trigger_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Selects the source of the trigger for the integration and
            envelope in Spectroscopy mode (default: "chan0trigin0"). \n
            To list the available options: \n
            >>> shf.qachannels[0].sweeper.trigger_source
    """

    def __init__(self, parent: SHFQAChannel) -> None:
        super().__init__(parent)
        self.oscillator_gain = None
        self.oscillator_freq = None
        self.integration_time = None
        self.integration_length = None
        self.integration_delay = None
        self.trigger_source = None
        self._trigger_level = 0.5
        self._trigger_imp50 = True
        self._start_freq = -300e6
        self._stop_freq = 300e6
        self._num_points = 100
        self._mapping = "linear"
        self._num_averages = 1
        self._averaging_mode = "cyclic"

    def _init_sweeper_params(self):
        self.oscillator_gain = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/oscs/0/gain"),
            device=self._device,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, 0.0),
            ],
        )
        self.oscillator_freq = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/oscs/0/freq"),
            device=self._device,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 500e6),
                lambda v: Parse.greater_equal(v, -500e6),
            ],
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
        self.integration_delay = Parameter(
            self,
            self._device._get_node_dict(f"qachannels/{self._index}/spectroscopy/delay"),
            device=self._device,
            set_parser=lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        )
        self.trigger_source = Parameter(
            self,
            self._device._get_node_dict(
                f"qachannels/{self._index}/spectroscopy/trigger/channel"
            ),
            device=self._device,
            auto_mapping=True,
        )

    def trigger_level(self, level=None):
        """Set or get the trigger level for the sweeper.

        Arguments:
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

        Arguments:
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

        Arguments:
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

        Arguments:
            freq (float): Stop frequency in Hz of the sweeper
                (default: None).

        """
        if freq is None:
            return self._stop_freq
        else:
            self._stop_freq = freq
        self._update_sweep_params()

    def output_freq(self):
        """Get the output frequency.

        Returns:
            The carrier frequency in Hz of the microwave signal at the
            Out connector. This frequency corresponds to the sum of the
            Center Frequency and the Offset Frequency.

        """
        return self._parent.center_freq() + self.oscillator_freq()

    def num_points(self, num=None):
        """Set or get the number of points for the sweeper.

        Arguments:
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

        Arguments:
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

        Arguments:
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

        Arguments:
            mode (str): Averaging mode for the sweeper. Can be either
                "sequential" or "cyclic" (default: None).\n
                "sequential": A frequency point is measured the number
                of times specified by the number of averages setting.
                In other words, the same frequency point is measured
                repeatedly until the number of averages is reached
                and the sweeper then moves to the next frequency
                point.\n
                "cyclic": All frequency points are measured once from
                start frequency to stop frequency. The sweeper then
                moves back to start frequency and repeats the sweep
                the number of times specified by the number of
                averages setting.

        """
        if mode is None:
            return self._averaging_mode
        else:
            self._averaging_mode = mode
        self._update_averaging_settings()


class Scope(SHFScope):
    """Device-specific Scope for SHFQA.

    This class inherits from the base :class:`SHFScope`  and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s such as channels,
    input_selects, trigger_source, trigger_delay, etc...

    Attributes:
        channel1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Enable recording for Scope channel 1. Can be either 'on' or
            'off' (default: 'off').
        channel2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Enable recording for Scope channel 2. Can be either 'on' or
            'off' (default: 'off').
        channel3 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Enable recording for Scope channel 3. Can be either 'on' or
            'off' (default: 'off').
        channel4 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Enable recording for Scope channel 4. Can be either 'on' or
            'off' (default: 'off').
        input_select1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the scope input signal for channel 1
            (default: 'chan0sigin'). \n
            To list the available options: \n
            >>> shf.scope.input_select1
        input_select2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the scope input signal for channel 2
            (default: 'chan0sigin'). \n
            To list the available options: \n
            >>> shf.scope.input_select2
        input_select3 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the scope input signal for channel 3
            (default: 'chan0sigin'). \n
            To list the available options: \n
            >>> shf.scope.input_select3
        input_select4 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the scope input signal for channel 4
            (default: 'chan0sigin'). \n
            To list the available options: \n
            >>> shf.scope.input_select4
        trigger_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Select the scope trigger source signal
            (default: 'chan0trigin0'). \n
            To list the available options: \n
            >>> shf.scope.trigger_source
        trigger_delay (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The delay of a Scope measurement. A negative delay results
            in data being acquired before the trigger point. The
            resolution is 2 ns (default: 0.0).
        length (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Length of the recorded Scope shot in number of samples
            It has a minimum value and a granularity of 16. Up to
            262.1 kSa (2^18 samples) can be recorded (default: 32).
            (default: 32).
        time (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Time base of the Scope (default: '2 GHz'). \n
            To list the available options: \n
            >>> shf.scope.time

    """

    def __init__(self, parent: BaseInstrument) -> None:
        super().__init__(parent)
        self._enable = None
        self.channel1 = None
        self.channel2 = None
        self.channel3 = None
        self.channel4 = None
        self.input_select1 = None
        self.input_select2 = None
        self.input_select3 = None
        self.input_select4 = None
        self._wave1 = None
        self._wave2 = None
        self._wave3 = None
        self._wave4 = None
        self.trigger_source = None
        self.trigger_delay = None
        self.length = None
        self.time = None
        self._segments_enable = None
        self._segments_count = None
        self._averaging_enable = None
        self._averaging_count = None

    def _init_scope_params(self):
        self._enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
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
            auto_mapping=True,
        )
        self.input_select2 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/1/inputselect"),
            device=self._parent,
            auto_mapping=True,
        )
        self.input_select3 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/2/inputselect"),
            device=self._parent,
            auto_mapping=True,
        )
        self.input_select4 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/3/inputselect"),
            device=self._parent,
            auto_mapping=True,
        )
        self._wave1 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/0/wave"),
            device=self._parent,
        )
        self._wave2 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/1/wave"),
            device=self._parent,
        )
        self._wave3 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/2/wave"),
            device=self._parent,
        )
        self._wave4 = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channels/3/wave"),
            device=self._parent,
        )
        self.trigger_source = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigger/channel"),
            device=self._parent,
            auto_mapping=True,
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
            set_parser=[
                lambda v: Parse.greater_equal(v, 16),
                lambda v: Parse.smaller_equal(v, 2 ** 18),
                lambda v: Parse.multiple_of(v, 16, "down"),
            ],
        )
        self.time = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/time"),
            device=self._parent,
            auto_mapping=True,
        )
        self._segments_enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/segments/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self._segments_count = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/segments/count"),
            device=self._parent,
            set_parser=lambda v: Parse.greater(v, 0),
        )
        self._averaging_enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/averaging/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self._averaging_count = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/averaging/count"),
            device=self._parent,
            set_parser=lambda v: Parse.greater(v, 0),
        )
