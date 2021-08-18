# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""Zurich Instruments Toolkit (zhinst-toolkit) UHFQA Driver.

This driver provides a high-level controller for the Zurich Instruments
UHFQA Quantum Analyzer for Zurich Instruments Toolkit (zhinst-toolkit).
It is based on our Python API ziPython and forms the basis for UHFQA
drivers used in QCoDeS and Labber.
"""

import numpy as np
from typing import List

from zhinst.toolkit.control.drivers.base import (
    BaseInstrument,
    AWGCore,
    Scope,
)
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
from zhinst.toolkit.helpers import SequenceType, TriggerMode

_logger = LoggerModule(__name__)

MAPPINGS = {
    "result_source": {
        0: "Crosstalk",
        1: "Threshold",
        2: "Rotation",
        4: "Crosstalk Correlation",
        5: "Threshold Correlation",
        7: "Integration",
    },
    "averaging_mode": {0: "Cyclic", 1: "Sequential"},
}


class UHFQA(BaseInstrument):
    """High-level driver for the Zurich Instruments UHFQA Quantum
    Analyzer.

    Inherits from :class:`BaseInstrument` and adds an :class:`AWGCore`
    and a list of :class:`ReadoutChannels`. They can be accessed as
    properties of the UHFQA.

        >>> import zhinst.toolkit as tk
        >>> ...
        >>> uhfqa = tk.UHFQA("uhfqa", "dev2000")
        >>> uhfqa.setup()
        >>> uhfqa.connect_device()
        >>> ...
        >>> uhfqa.nodetree
        <zhinst.toolkit.tools.node_tree.NodeTree object at 0x0000021091FFC898>
        nodes:
        - stats
        - osc
        - triggers
        - status
        - dio
        - auxin
        - scope
        - system
        - sigins
        - sigouts
        - features
        - auxouts
        - awg
        - qa
        parameters:
        - clockbase

    A measurement using the *AWG Core* could look like this:

        >>> uhfqa.awg.set_sequence_params(...)
        >>> uhfqa.channels[0].enable()
        >>> uhfqa.channels[0].readout_frequency(123e6)
        >>> uhfqa.qa_delay(8) # adjust quantum analyzer delay
        >>> ...
        >>> uhfqa.arm(length=100, averages=1)   # arm the QA Readout, set length and averages
        >>> uhfqa.awg.run()                     # start the AWG
        >>> uhfqa.awg.wait_done()               # wait until AWG is finished
        >>> result = uhfqa.channels[0].result() # get the result vector

    Arguments:
        name (str): Identifier for the UHFQA.
        serial (str): Serial number of the device, e.g. *'dev2000'*. The
            serial number can be found on the back panel of the
            instrument.
        discovery: an instance of ziDiscovery

    Attributes:
        awg (:class:`zhinst.toolkit.control.drivers.uhfqa.AWG`):
            A device-specific :class:`AWGCore` for the UHFQA.
        channels (list): A list of ten
            :class:`zhinst.toolkit.control.drivers.uhfqa.ReadoutChannel` s
            that each represent the digital signal processing path on
            the instrument.
        allowed_sequences (list): A list of :class:`SequenceType` s
            that the instrument supports.
        allowed_trigger_modes (list): A list of :class:`TriggerMode` s
            that the instrument supports.
        integration_time (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The time in seconds used for signal integration. The value
            must be greater than and multiple of 2.222 ns. The maximum
            value when using weighted integration is ca. 2.275 us
            (default: 2.0 us).
        integration_length (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The integration length in number of samples. The value
            must be gerater than and multiple of 4. The maximum value
            when using weighted integration is 4096 samples
            (default: 4096).
        result_source (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            This parameter selects the stage in the signal processing
            path that is used as the source for the QA results. It can
            be one of {`"Crosstalk"`, `"Threshold"`, `"Rotation"`,
            `"Crosstalk Correlation"`, `"Threshold Correlation"`,
            `"Integration"`}.
        averaging_mode (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Mode of averaing in the QA Result Acquisition. Either
            `"Sequential"` or `"Cyclic"`.
            `"Sequential"`: The first point of the Result vector is the
            average of the first *N* results where *N* is the value of
            the *result averages* setting. The second point is the
            average of the next *N* results, and so forth.
            `"Cyclic"`: The first point in the Result vector is the
            average of the results *1, M+1, 2M+1, ...*, where *M* is
            the value of the *result length* setting. The second point
            is the average of the results number *2, M+2, 2M+2, ...*,
            and so forth.
        ref_clock (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Clock source used as the frequency and time base reference.
            Either `0: "internal"` or `1: "external"`.
            `0: "internal`: Internal 10 MHz clock
            `1: "external`: An external 10 MHz clock. Provide a clean
            and stable 10 MHz reference to the appropriate back panel
            connector.
    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.UHFQA, serial, discovery, **kwargs)
        self._awg = None
        self._channels = []
        self.integration_time = None
        self.integration_length = None
        self.result_source = None
        self.averaging_mode = None
        self.ref_clock = None
        self._qa_delay_user = 0
        self._allowed_sequences = [
            SequenceType.NONE,
            SequenceType.SIMPLE,
            SequenceType.READOUT,
            SequenceType.CW_SPEC,
            SequenceType.PULSED_SPEC,
            SequenceType.CUSTOM,
        ]
        self._allowed_trigger_modes = [
            TriggerMode.NONE,
            TriggerMode.EXTERNAL_TRIGGER,
            TriggerMode.RECEIVE_TRIGGER,
            TriggerMode.ZSYNC_TRIGGER,
        ]

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server and initializes the
        AWG.

        Arguments:
            nodetree (bool): A flag that specifies if all the
                parameters from the device's nodetree should be added
                to the object's attributes as `zhinst-toolkit`
                Parameters (default: True).

        """
        super().connect_device(nodetree=nodetree)
        self._init_awg_cores()
        self._init_scope()
        self._init_readout_channels()

    def factory_reset(self, sync=True) -> None:
        """Load the factory default settings.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).

        """
        super().factory_reset(sync=sync)
        # Set the AWG to single shot mode manually since the firmware
        # is not programmed to do this automatically when factory
        # preset is loaded
        self.awg.single(True)
        self.qa_delay(0)

    def crosstalk_matrix(self, matrix=None):
        """Sets or gets the crosstalk matrix of the UHFQA as a 2D array.

        Arguments:
            matrix (2D array): The 2D matrix used in the digital signal
                processing path to compensate for crosstalk between the
                different channels. The given matrix can also be a part
                of the entire 10 x 10 matrix. Its maximum dimensions
                are 10 x 10 (default: None).

        Returns:
            If no argument is given the method returns the current
            crosstalk matrix as a 2D numpy array.

        Raises:
            ValueError: If the matrix size exceeds the maximum size of
                10 x 10

        """
        if matrix is None:
            m = np.zeros((10, 10))
            for r in range(10):
                for c in range(10):
                    m[r, c] = self._get(f"qas/0/crosstalk/rows/{r}/cols/{c}")
            return m
        else:
            rows, cols = matrix.shape
            if rows > 10 or cols > 10:
                _logger.error(
                    f"The shape of the given matrix is {rows} x {cols}. "
                    f"The maximum size is 10 x 10.",
                    _logger.ExceptionTypes.ValueError,
                )
            for r in range(rows):
                for c in range(cols):
                    self._set(f"qas/0/crosstalk/rows/{r}/cols/{c}", matrix[r, c])

    def enable_readout_channels(self, channels: List = range(10)) -> None:
        """Enable weighted integration on the specified readout
         channels.

        Arguments:
            channels (list): A list of indices of channels to enable.
                (default: range(10))

        Raises:
            ValueError: If the channel list contains an element outside
                the allowed range.

        """
        for i in channels:
            if i not in range(10):
                _logger.error(
                    f"The channel index {i} is out of range!",
                    _logger.ExceptionTypes.ValueError,
                )
            self.channels[i].enable()

    def disable_readout_channels(self, channels: List = range(10)) -> None:
        """Disables weighted integration on the specified readout
        channels.

        Arguments:
            channels (list): A list of indices of channels to disable.
                (default: range(10))

        Raises:
            ValueError: If the channel list contains an element outside
                the allowed range.

        """
        for i in channels:
            if i not in range(10):
                _logger.error(
                    f"The channel index {i} is out of range!",
                    _logger.ExceptionTypes.ValueError,
                )
            self.channels[i].disable()

    def enable_qccs_mode(self) -> None:
        """Configure the instrument to work with PQSC.

        This method sets the reference clock source and DIO settings
        correctly to connect the instrument to the PQSC.
        """
        settings = [
            # Use external 10 MHz clock as reference
            ("/system/extclk", "external"),
            # Configure DIO
            # Clock DIO internally with a frequency of 50 MHz
            ("/dios/0/extclk", "internal"),
            # Set DIO output values to QA results compatible with QCCS.
            ("/dios/0/mode", "qa_result_qccs"),
            # Drive the two least significant bytes of the DIO port
            ("/dios/0/drive", 0b0011),
        ]
        self._set(settings)

    def enable_manual_mode(self) -> None:
        """Disconnect from the PQSC.

        This method sets the reference clock source and DIO settings to
        factory default states and the instrument is disconnected from
        the PQSC.
        """
        settings = [
            # Use internal clock as reference
            ("/system/extclk", "internal"),
            # Configure DIO settings to factory default values
            # Clock DIO internally with a frequency of 56.25 MHz
            ("/dios/0/extclk", 0),
            # Enable manual control of the DIO output bits
            ("/dios/0/mode", "manual"),
            # Disable drive for all DIO bits
            ("/dios/0/drive", 0b0000),
        ]
        self._set(settings)

    def arm(self, length=None, averages=None) -> None:
        """Prepare UHFQA for result acquisition.

        This method enables the QA Results Acquisition and resets the
        acquired points. Optionally, the *result length* and
        *result averages* can be set when specified as keyword
        arguments. If they are not specified,they are not changed.

        Arguments:
            length (int): If specified, the length of the result vector
                will be set before arming the UHFQA readout
                (default: None).
            averages (int): If specified, the result averages will be
                set before arming the UHFQA readout (default: None).

        """
        if length is not None:
            self._set("qas/0/result/length", int(length))
        if averages is not None:
            self._set("qas/0/result/averages", int(averages))
        self._set("qas/0/result/enable", 1)
        # toggle node value from 0 to 1 for reset
        self._set("qas/0/result/reset", 0)
        self._set("qas/0/result/reset", 1)

    def qa_delay(self, value=None):
        """Set or get the adjustment in the the quantum analyzer delay.

        Arguments:
            value (int): Number of additional samples to adjust the
                delay (default: None)

        Returns:
            The adjustment in delay in units of samples.

        Raises:
            ValueError: If the adjusted quantum analyzer delay is
                outside the allowed range.

        """
        node = f"qas/0/delay"
        # Return the current adjustment if no argument is passed
        if value is None:
            return self._qa_delay_user
        else:
            # Round down to greatest multiple of 4, as in LabOne
            qa_delay_user_temp = int(value // 4) * 4
            # Calculate final value of adjusted QA delay.
            qa_delay_adjusted = qa_delay_user_temp + self._qa_delay_default()
            # Check if final delay is between 0 and 1020
            if qa_delay_adjusted not in range(0, 1021):
                _logger.error(
                    "The quantum analyzer delay is out of range!",
                    _logger.ExceptionTypes.ValueError,
                )
            else:
                # Overwrite the previous adjustment if range is correct
                self._qa_delay_user = qa_delay_user_temp
                # Write the adjusted delay value to the node
                self._set(node, qa_delay_adjusted)
                # Return the final adjustment
                return self._qa_delay_user

    def _qa_delay_default(self):
        """Return the default value for the quantum analyzer delay.

        Quantum analyzer delay adjusts the time at which the
        integration starts in relation to the trigger signal of the
        weighted integration units.

        The default delay value is:
        184 samples if deskew matrix is bypassed
        200 samples if deskew matrix is active

        """
        node = f"qas/0/bypass/deskew"
        # Check if deskew is bypassed or not
        if self._get(node):
            return 184
        else:
            return 200

    def _init_awg_cores(self):
        """Initialize the AWGs cores of the device."""
        self._awg = AWG(self, 0)
        self.awg._setup()
        self.awg._init_awg_params()

    def _init_readout_channels(self):
        """Initialize the readout channels of the device."""
        self._channels = [ReadoutChannel(self, i) for i in range(10)]
        [channel._init_channel_params() for channel in self.channels]

    def _init_scope(self):
        """Initialize the Scope of the device."""
        self._scope = UHFScope(self)
        self.scope._setup()
        self.scope._init_scope_params()
        self.scope._init_scope_settings()

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        super()._init_params()
        self.integration_time = Parameter(
            self,
            dict(
                Node=f"{self.serial}/qas/0/integration/length".upper(),
                Description="The integration time of all weighted integration units "
                "specified in seconds. In Standard mode, a maximum of 4096 "
                "samples can be integrated, which corresponds to 2.3 µs. "
                "In Spectroscopy mode, a maximum of 16.7 MSa can be "
                "integrated, which corresponds to ~10 ms.",
                Type="Double",
                Properties="Read, Write, Setting",
                Unit="s",
            ),
            device=self,
            set_parser=Parse.uhfqa_time2samples,
            get_parser=Parse.uhfqa_samples2time,
        )
        self.integration_length = Parameter(
            self,
            self._get_node_dict("qas/0/integration/length"),
            device=self,
            set_parser=[
                lambda v: Parse.greater_equal(v, 4),
                lambda v: Parse.multiple_of(v, 4, "down"),
            ],
        )
        self.result_source = Parameter(
            self,
            self._get_node_dict("qas/0/result/source"),
            device=self,
            mapping=MAPPINGS["result_source"],
        )
        self.averaging_mode = Parameter(
            self,
            self._get_node_dict("qas/0/result/mode"),
            device=self,
            mapping=MAPPINGS["averaging_mode"],
        )
        self.ref_clock = Parameter(
            self,
            self._get_node_dict(f"system/extclk"),
            device=self,
            auto_mapping=True,
        )

    def _init_settings(self):
        settings = [
            # Enable single shot mode of AWG
            ("awgs/0/single", 1),
        ]
        self._set(settings)
        # Set quantum analyzer delay adjustment to 0
        self.qa_delay(0)

    @property
    def awg(self):
        return self._awg

    @property
    def scope(self):
        return self._scope

    @property
    def channels(self):
        return self._channels

    @property
    def allowed_sequences(self):
        return self._allowed_sequences

    @property
    def allowed_trigger_modes(self):
        return self._allowed_trigger_modes


class AWG(AWGCore):
    """Device-specific AWG Core for UHFQA.

    Inherits from `AWGCore` and adds
    :mod:`zhinst-toolkit` :class:`Parameter` s like output or gains.
    This class also specifies sequence specific settings for the UHFQA.

        >>> uhf.awg
        <zhinst.toolkit.control.drivers.uhfqa.AWG object at 0x000001E20BD98908>
            parent  : <zhinst.toolkit.control.drivers.uhfqa.UHFQA object at 0x000001E20BC754C8>
            index   : 0
            sequence:
                type: SequenceType.NONE
                ('target', <DeviceTypes.UHFQA: 'uhfqa'>)
                ('clock_rate', 1800000000.0)
                ('period', 0.0001)
                ('trigger_mode', <TriggerMode.NONE: 'None'>)
                ('trigger_samples', 32)
                ('repetitions', 1)
                ('alignment', <Alignment.END_WITH_TRIGGER: 'End with Trigger'>)
                ...

        >>> uhf.awg.outputs(["on", "on"])
        >>> uhf.awg.single(True)
        >>> uhf.awg.gain1()
        1.0

    Attributes:
        output1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The state of the output of channel 1. Can be one of
            {'on', 'off'}.
        output2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The state of the output of channel 2. Can be one of
            {'on', 'off'}.
        gain1 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the output channel 1. The value must be between
            -1 and +1 (default: +1).
        gain2 (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Gain of the output channel 2. The value must be between
            -1 and +1 (default: +1).
        single (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            State of the AWG single shot mode, i.e. one of
            {True, False} (default: True).

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        super().__init__(parent, index)
        self._enable = None
        self.output1 = None
        self.output2 = None
        self.gain1 = None
        self.gain2 = None
        self.single = None

    def _init_awg_params(self):
        self._enable = Parameter(
            self,
            self._parent._get_node_dict(f"awgs/0/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.output1 = Parameter(
            self,
            self._parent._get_node_dict("sigouts/0/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.output2 = Parameter(
            self,
            self._parent._get_node_dict("sigouts/1/on"),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.gain1 = Parameter(
            self,
            self._parent._get_node_dict("awgs/0/outputs/0/amplitude"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.gain2 = Parameter(
            self,
            self._parent._get_node_dict("awgs/0/outputs/1/amplitude"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        )
        self.single = Parameter(
            self,
            self._parent._get_node_dict("awgs/0/single"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )

    def _apply_sequence_settings(self, **kwargs) -> None:
        super()._apply_sequence_settings(**kwargs)
        if "sequence_type" in kwargs.keys() and kwargs["sequence_type"] != "None":
            t = SequenceType(kwargs["sequence_type"])
            # apply settings depending on the sequence type
            if t == SequenceType.CW_SPEC:
                self._apply_cw_settings()
            elif t == SequenceType.PULSED_SPEC:
                self._apply_pulsed_settings()
            elif t == SequenceType.READOUT:
                self._apply_readout_settings()
            else:
                self._apply_base_settings()
        if "trigger_mode" in kwargs.keys() and kwargs["trigger_mode"] != "None":
            t = TriggerMode(kwargs["trigger_mode"])
            # apply settings depending on trigger mode
            if t in [TriggerMode.EXTERNAL_TRIGGER, TriggerMode.RECEIVE_TRIGGER]:
                self._apply_receive_trigger_settings()
            elif t == TriggerMode.ZSYNC_TRIGGER:
                self._apply_zsync_trigger_settings()

    def _apply_base_settings(self):
        settings = [
            ("sigouts/*/enables/*", 0),
            ("sigouts/*/amplitudes/*", 0),
            ("awgs/0/outputs/*/mode", 0),
            ("qas/0/integration/mode", 0),
        ]
        self._parent._set(settings)

    def _apply_cw_settings(self):
        settings = [
            ("sigouts/0/enables/0", 1),
            ("sigouts/1/enables/1", 1),
            ("sigouts/0/amplitudes/0", 1),
            ("sigouts/1/amplitudes/1", 1),
            ("awgs/0/outputs/*/mode", 0),
            ("qas/0/integration/mode", 1),
        ]
        self._parent._set(settings)
        self._parent.disable_readout_channels(range(10))

    def _apply_pulsed_settings(self):
        settings = [
            # Enable modulation mode of AWG to modulate two output
            # channels with *sine* and *cosine* of internal oscillator.
            ("awgs/0/outputs/0/mode", "modulation"),
            ("awgs/0/outputs/1/mode", "modulation"),
            # Enable sine generator 0 to Wave output 0 and
            # sine generator 1 to Wave output 1
            ("sigouts/0/enables/0", 1),
            ("sigouts/1/enables/1", 1),
            # Set amplitudes of the sine generators to zero, so they
            # are enabled, but no continuous wave output is produced.
            ("sigouts/0/amplitudes/0", 0),
            ("sigouts/1/amplitudes/1", 0),
            # Set the integration mod to the spectroscopy mode to
            # demodulate the input signals with the *sine* and *cosine*
            # of the same internal oscillator
            ("qas/0/integration/mode", "spectroscopy"),
            # Configure two readout channels such that their outputs are
            # equal to real and imaginary part of the complex amplitude
            ("qas/0/bypass/rotation", 0),  # Do not bypass rotation
            ("qas/0/integration/sources/0", "sigin1_real_sigin0_imag"),
            ("qas/0/rotations/0", 1 - 1j),
            ("qas/0/integration/sources/1", "sigin0_real_sigin1_imag"),
            ("qas/0/rotations/1", 1 + 1j),
            # Result after Rotation unit
            ("qas/0/result/source", "result_after_rotation_unit"),
        ]
        # Apply the settings above
        self._parent._set(settings)
        # Set the Quantum Analyzer delay. Enabling of deskew matrix and
        # previous user adjustment are taken into account automatically.
        self._parent.qa_delay(self._parent._qa_delay_user)
        # Disable readout channels
        self._parent.disable_readout_channels(range(10))

    def _apply_readout_settings(self):
        settings = [
            ("sigouts/*/enables/*", 0),
            ("awgs/0/outputs/*/mode", 0),
            ("qas/0/integration/mode", 0),
        ]
        self._parent._set(settings)

    def _apply_receive_trigger_settings(self):
        settings = [
            ("/awgs/0/auxtriggers/*/channel", 0),
            ("/awgs/0/auxtriggers/*/slope", 1),
        ]
        self._parent._set(settings)

    def _apply_zsync_trigger_settings(self):
        settings = [
            # Configure DIO triggering based on HDAWG DIO protocol
            # Set signal edge of the STROBE signal to off
            ("/awgs/0/dio/strobe/slope", "off"),
            # Set VALID bit polarity to indicate that input is valid
            ("/awgs/0/dio/valid/polarity", "high"),
            # Set DIO bit to use as VALID signal to indicate valid input
            ("/awgs/0/dio/valid/index", 16),
        ]
        self._parent._set(settings)

    def update_readout_params(self) -> None:
        """Update the readout parameters for 'Readout' sequence

        This method gets the frequency, amplitude and phase shift
        values from the readout channels and uses them to update the
        sequence parameters.

        Raises:
            ToolkitError: If the selected sequence type is not
                'Readout'
        """
        if self.sequence_params["sequence_type"] == SequenceType.READOUT:
            freqs = []
            amps = []
            phases = []
            for ch in self._parent.channels:
                if ch.enabled():
                    freqs.append(ch.readout_frequency())
                    amps.append(ch.readout_amplitude())
                    phases.append(ch.phase_shift())
            self.set_sequence_params(
                readout_frequencies=freqs,
                readout_amplitudes=amps,
                phase_shifts=phases,
            )
        else:
            _logger.error(
                "AWG Sequence type needs to be 'Readout'",
                _logger.ExceptionTypes.ToolkitError,
            )

    def compile(self) -> None:
        """Wrap the 'compile(...)' method of the parent class
        `AWGCore`."""
        if self.sequence_params["sequence_type"] == SequenceType.READOUT:
            self.update_readout_params()
        super().compile()


class ReadoutChannel:
    """Implements a Readout Channel for UHFQA.

    This class represents the signal processing chain for one of the
    ten :class:`ReadoutChannels` of a UHFQA. One channel is typically
    used for dispersive resonator readout of superconducting qubits.

        >>> ch = uhfqa.channels[0]
        >>> uhfqa.result_source("Threshold")
        >>> ...
        >>> ch.enable()
        >>> ch.readout_frequency(85.6e6)
        >>> ch
        Readout Channel 0:  <zhinst.toolkit.uhfqa.ReadoutChannel object at 0x0000021091FD4F28>
            rotation          : 0.0
            threshold         : 0.0
            readout_frequency : 85600000.0
            readout_amplitude : 1
            phase_shift       : 0
        >>> ch.rotation(123.4)
        >>> ch.threshold(-56.78)
        >>> ...
        >>> ch.result()
        array([0.0, 1.0, 1.0, 1.0, 0.0, ...])

    The readout channel can be enabled with `enable()` which means that
    the weighted integration mode is activated and integration weights
    are set to demodulate the signal at the given readout frequency. If
    the channel is enabled, the readout parameters are also used for
    signal generation in the :class:`AWGCore` if the sequence type is
    set to *'Readout'*.

    Attributes:
        index (int): The index of the Readout Channel from 1 - 10.
        rotation (:class:`zhinst.toolkit.control.nodetree.Parameter`):
            The rotation applied to the signal in IQ plane. The angle
            is specified in degrees.
        threshold (:class:`zhinst.toolkit.control.nodetree.Parameter`):
            The signal threshold used for state discrimination in the
            thresholding unit.
        result (:class:`zhinst.toolkit.control.nodetree.Parameter`):
            This read-only Parameter holds the result vector for the
            given readout channel as a 1D numpy array.

    Raises:
        ValueError: If the channel index is not in the allowed range.

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        if index not in range(10):
            _logger.error(
                f"The channel index {index} is out of range!",
                _logger.ExceptionTypes.ValueError,
            )
        self._index = index
        self._parent = parent
        self._enabled = False
        self._readout_frequency = 100e6
        self._readout_amplitude = 1
        self._int_weights_envelope = 1.0
        self._phase_shift = 0
        self.rotation = None
        self.threshold = None
        self.result = None

    def _init_channel_params(self):
        self.rotation = Parameter(
            self,
            self._parent._get_node_dict(f"qas/0/rotations/{self._index}"),
            device=self._parent,
            set_parser=Parse.deg2complex,
            get_parser=Parse.complex2deg,
        )
        self.threshold = Parameter(
            self,
            self._parent._get_node_dict(f"qas/0/thresholds/{self._index}/level"),
            device=self._parent,
        )
        self.result = Parameter(
            self,
            self._parent._get_node_dict(f"qas/0/result/data/{self._index}/wave"),
            device=self._parent,
            get_parser=self._average_result,
        )

    @property
    def index(self):
        return self._index

    def enabled(self) -> bool:
        """Returns if weighted integration is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable weighted integration for this channel. 
        
        This enables weighted integration mode and sets the 
        corresponding integration weights to  demodulate at the given 
        readout frequency.
        """
        self._enabled = True
        self._parent._set("qas/0/integration/mode", 0)
        self._set_int_weights()

    def disable(self) -> None:
        """Disable weighted integration for this channel.

        This method also resets the corresponding integration weights.
        """
        self._enabled = False
        self._reset_int_weights()

    def readout_frequency(self, freq=None):
        """Sets or gets the readout frequency for this channel.

        Readout frequency in Hz of the readout channel. If the AWG
        :class:`SequenceProgram` is of type "Readout", this Parameter
        is used to generate a readout tone at the given readout
        frequency for all readout channels that are enabled. This
        frequency is also used in the signal acquisition for digital
        demodulation if the readout channel is enabled. The frequency
        must be positive.

        """
        if freq is None:
            return self._readout_frequency
        else:
            Parse.greater(freq, 0)
            self._readout_frequency = freq
            self._set_int_weights()
            return self._readout_frequency

    def int_weights_envelope(self, envelope=None):
        """Set or get the envelope multiplied with the integration
        weights.

        Arguments:
            envelope (list or double): Envelope value or list of values
                to be multiplied with the integration weights. Each
                value must be between 0.0 and 1.0 (default: 1.0).
        Raises:
            ToolkitError: If integration weight envelope is given as a
                list or array but the length of the list does not match
                the integration length.

        """
        if envelope is None:
            return self._int_weights_envelope
        else:
            if isinstance(envelope, list) or isinstance(envelope, np.ndarray):
                if len(envelope) == self._parent.integration_length():
                    for i in range(len(envelope)):
                        envelope[i] = Parse.greater_equal(envelope[i], 0)
                        envelope[i] = Parse.smaller_equal(envelope[i], 1.0)
                else:
                    _logger.error(
                        "The length of `int_weights_envelope` list must be equal to "
                        "integration length.",
                        _logger.ExceptionTypes.ToolkitError,
                    )
            else:
                envelope = Parse.greater_equal(envelope, 0)
                envelope = Parse.smaller_equal(envelope, 1.0)
            self._int_weights_envelope = envelope
            self._set_int_weights()
            return self._int_weights_envelope

    def readout_amplitude(self, amp=None):
        """Sets or gets the readout amplitude for this channel.

        The amplitude of the readout pulse is used for signal
        generation of the readout tone if the channel is enabled and if
        the AWG :class:`SequenceProgram` is of type *'Readout'*
        (default: 1.0).

        """
        if amp is None:
            return self._readout_amplitude
        else:
            Parse.smaller_equal(amp, 1.0)
            Parse.greater_equal(amp, -1.0)
            self._readout_amplitude = amp
            return self._readout_amplitude

    def phase_shift(self, ph=None):
        """Sets or gets the readout phase shift for this channel.

        Additional phase shift in the signal generation between I and Q
        quadratures. (default: 0)

        """
        if ph is None:
            return self._phase_shift
        else:
            self._phase_shift = Parse.phase(ph)
            return self._phase_shift

    def _reset_int_weights(self):
        node = f"/qas/0/integration/weights/"
        self._parent._set(node + f"{self._index}/real", np.zeros(4096))
        self._parent._set(node + f"{self._index}/imag", np.zeros(4096))

    def _set_int_weights(self):
        self._reset_int_weights()
        length = self._parent.integration_length()
        freq = self.readout_frequency()
        envelope = self.int_weights_envelope()
        node = f"/qas/0/integration/weights/{self._index}/"
        _demod_weights = self._demod_weights(length, envelope, freq, 0)
        _demod_weights_real = np.ascontiguousarray(np.real(_demod_weights))
        _demod_weights_imag = np.ascontiguousarray(np.imag(_demod_weights))
        self._parent._set_vector(node + "real", _demod_weights_real)
        self._parent._set_vector(node + "imag", _demod_weights_imag)

    @staticmethod
    def _demod_weights(length, envelope, freq, phase):
        if length > 4096:
            _logger.error(
                "The maximum length of the integration weights is 4096 samples.",
                _logger.ExceptionTypes.ValueError,
            )
        if freq <= 0:
            _logger.error(
                "This frequency must be positive.",
                _logger.ExceptionTypes.ValueError,
            )
        clk_rate = 1.8e9
        x = np.arange(0, length, 1)
        y_real = envelope * np.cos(2 * np.pi * freq * x / clk_rate + np.deg2rad(phase))
        y_imag = envelope * np.sin(2 * np.pi * freq * x / clk_rate + np.deg2rad(phase))
        y = y_real + 1j * y_imag
        return y

    def _average_result(self, result):
        n_averages = self._parent._get("qas/0/result/averages")
        return result / n_averages

    def __repr__(self):
        s = f"Readout Channel {self._index}:  {super().__repr__()}\n"
        s += f"     rotation          : {self.rotation()}\n"
        s += f"     threshold         : {self.threshold()}\n"
        if self._enabled:
            s += f"     readout_frequency : {self.readout_frequency()}\n"
            s += f"     readout_amplitude : {self.readout_amplitude()}\n"
            s += f"     phase_shift       : {self.phase_shift()}\n"
        else:
            s += "      Weighted Integration Disabled\n"
        return s


class UHFScope(Scope):
    """Device-specific Scope for UHFQA.

    This class inherits from the base :class:`Scope`  and adds
    :mod:`zhinst-toolkit` :class:`.Parameter` s.

    """

    def __init__(self, parent: BaseInstrument) -> None:
        super().__init__(parent)
        self._enable = None
        self.single = None
        self.length = None
        self._channel = None
        self.trigger_source = None
        self.trigger_level = None
        self.trigger_enable = None
        self.trigger_reference = None
        self.trigger_holdoff = None

    def _init_scope_params(self):
        self._enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/enable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.single = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/single"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.length = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/length"),
            device=self._parent,
            set_parser=[
                lambda v: Parse.greater_equal(v, 4096),
                lambda v: Parse.smaller_equal(v, 128000000),
                lambda v: Parse.multiple_of(v, 16, "down"),
            ],
        )
        self._channel = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/channel"),
            device=self._parent,
        )
        self.trigger_source = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigchannel"),
            device=self._parent,
            auto_mapping=True,
        )
        self.trigger_level = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/triglevel"),
            device=self._parent,
        )
        self.trigger_enable = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigenable"),
            device=self._parent,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.trigger_reference = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigreference"),
            device=self._parent,
        )
        self.trigger_holdoff = Parameter(
            self,
            self._parent._get_node_dict(f"scopes/0/trigholdoff"),
            device=self._parent,
        )
