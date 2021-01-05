# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
from typing import List

from zhinst.toolkit.control.drivers.base import BaseInstrument, AWGCore, ToolkitError
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes
from zhinst.toolkit.helpers import SequenceType, TriggerMode


MAPPINGS = {
    "result_source": {
        0: "Crosstalk",
        1: "Threshold",
        2: "Rotation",
        4: "Crosstalk Correlation",
        5: "Threshold Correlation",
        7: "Integration",
    },
    "averaging_mode": {0: "Cyclic", 1: "Sequential",},
}


class UHFQA(BaseInstrument):
    """High-level driver for the Zurich Instruments UHFQA Quantum Analyzer. 
    
    Inherits from :class:`BaseInstrument` and adds an :class:`AWGCore` and a 
    list of :class:`ReadoutChannels`. They can be accessed as properties of the 
    UHFQA.

        >>> import zhinst.toolkit as tk
        >>> ...
        >>> uhfqa = tk.UHFQA("uhfqa", "dev1111")
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
        >>> ...
        >>> uhfqa.arm(length=100, averages=1)   # arm the QA Readout, set length and averages 
        >>> uhfqa.awg.run()                     # start the AWG    
        >>> uhfqa.awg.wait_done()               # wait until AWG is finished
        >>> result = uhfqa.channels[0].result() # get the result vector

    Arguments:
        name (str): Identifier for the UHFQA.
        serial (str): Serial number of the device, e.g. *'dev1234'*. The serial 
            number can be found on the back panel of the instrument.
        discovery: an instance of ziDiscovery

    Attributes:
        awg (:class:`zhinst.toolkit.control.drivers.uhfqa.AWG`): 
            A device-specific :class:`AWGCore` for the UHFQA.
        channels (list): A list of ten 
            :class:`zhinst.toolkit.control.drivers.uhfqa.ReadoutChannel` s that 
            each represent the digital signal processing path on the instrument.
        integration_time (:class:`zhinst.toolkit.control.node_tree.Parameter`): 
            The time in seconds used for signal integration. The value must be 
            positive. The maximum value when using weighted integration is 4096 
            samples or ca. 2.275 us (default: 2.0 us).
        result_source (:class:`zhinst.toolkit.control.node_tree.Parameter`): 
            This parameter selects the stage in the signal processing path that 
            is used as the source for the QA results. It can be one of 
            {`"Crosstalk"`, `"Threshold"`, `"Rotation"`, `"Crosstalk 
            Correlation"`, `"Threshold Correlation"`, `"Integration"`}. 
        averaging_mode (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Mode of averaing in the QA Result Acquisition. Either `"Sequential"` 
            or `"Cyclic"`.
            `"Sequential"`: The first point of the Result vector is the average 
            of the first *N* results where *N* is the value of the *result 
            averages* setting. The second point is the average of the next *N* 
            results, and so forth.
            `"Cyclic"`: The first point in the Result vector is the average of 
            the results *1, M+1, 2M+1, ...*, where *M* is the value of the 
            *result length* setting. The second point is the average of the 
            results number *2, M+2, 2M+2, ...*, and so forth.
              


    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.UHFQA, serial, discovery, **kwargs)
        self._awg = AWG(self, 0)
        self._channels = [ReadoutChannel(self, i) for i in range(10)]
        self.integration_time = Parameter(
            self,
            dict(
                Node="qas/0/integration/length",
                Description="The integration time of the QA Integration unit.",
                Type="Double",
                Properties="Read, Write",
                Unit="s",
            ),
            device=self,
            set_parser=Parse.uhfqa_time2samples,
            get_parser=Parse.uhfqa_samples2time,
        )
        self.result_source = Parameter(
            self,
            dict(
                Node="qas/0/result/source",
                Description="The signal source for the QA Results unit. One of {'Crosstalk', 'Threshold', 'Rotation', 'Crosstalk Correlation', 'Threshold Correlation', 'Integration'}.",
                Type="Integer",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self,
            mapping=MAPPINGS["result_source"],
        )
        self.averaging_mode = Parameter(
            self,
            dict(
                Node="qas/0/result/mode",
                Description="Selects the order of the result logger. One of {'Cyclic', 'Sequential'}.",
                Type="Integer",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self,
            mapping=MAPPINGS["averaging_mode"],
        )

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server and initializes the AWG.
        
        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from 
                the device's nodetree should be added to the object's attributes 
                as `zhinst-toolkit` Parameters. (default: True)
        
        """
        super().connect_device(nodetree=nodetree)
        self.awg._setup()

    def crosstalk_matrix(self, matrix=None):
        """Sets or gets the crosstalk matrix of the UHFQA as a 2D array.
        
        Keyword Arguments:
            matrix (2D array): The 2D matrix used in the digital signal 
                processing path to compensate for crosstalk between the 
                different channels. The given matrix can also be a part of the 
                entire 10 x 10 matrix. Its maximum dimensions are 10 x 10. 
                (default: None)

        Returns:
            If no argument is given the method returns the current crosstalk 
            matrix as a 2D numpy array.
        
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
                raise ValueError(
                    f"The shape of the given matrix is {rows} x {cols}. The maximum size is 10 x 10."
                )
            for r in range(rows):
                for c in range(cols):
                    self._set(f"qas/0/crosstalk/rows/{r}/cols/{c}", matrix[r, c])

    def enable_readout_channels(self, channels: List = range(10)) -> None:
        """Enables weighted integration on the specified readout channels.
        
        Keyword Arguments:
            channels (list): A list of indices of channels to enable. 
                (default: range(10))
        
        """
        for i in channels:
            if i not in range(10):
                raise ValueError(f"The channel index {i} is out of range!")
            self.channels[i].enable()

    def disable_readout_channels(self, channels: List = range(10)) -> None:
        """Disables weighted integration on the specified readout channels.
        
        Keyword Arguments:
            channels (list): A list of indices of channels to disable. 
                (default: range(10))
        
        """
        for i in channels:
            if i not in range(10):
                raise ValueError(f"The channel index {i} is out of range!")
            self.channels[i].disable()

    def arm(self, length=None, averages=None) -> None:
        """Prepare UHFQA for result acquisition.

        This method enables the QA Results Acquisition and resets the acquired 
        points. Optionally, the *result length* and *result averages* can be set 
        when specified as keyword arguments. If they are not specified, they are 
        not changed.  

        Keyword Arguments:
            length (int): If specified, the length of the result vector will be 
                set before arming the UHFQA readout. (default: None)
            averages (int): If specified, the result averages will be set before 
                arming the UHFQA readout. (default: None)

        """
        if length is not None:
            self._set("qas/0/result/length", int(length))
        if averages is not None:
            self._set("qas/0/result/averages", int(averages))
        self._set("qas/0/result/enable", 1)
        # toggle node value from 0 to 1 for reset
        self._set("qas/0/result/reset", 0)
        self._set("qas/0/result/reset", 1)

    def _init_settings(self):
        settings = [
            ("awgs/0/single", 1),
        ]
        self._set(settings)

    @property
    def awg(self):
        return self._awg

    @property
    def channels(self):
        return self._channels


class AWG(AWGCore):
    """Device-specific AWG Core for UHFQA.
    
    Inherits from `AWGCore` and adds :mod:`zhinst-toolkit` :class:`Parameters` 
    like ouput or gains. This class also specifies sequence specific settings 
    for the UHFQA.

    Attributes:
        output1 (:class:`zhinst.toolkit.control.node_tree.Parameter`): The state 
            of the output of channel 1. Can be one of {'on', 'off'}.
        output2 (:class:`zhinst.toolkit.control.node_tree.Parameter`): The state 
            of the output of channel 2. Can be one of {'on', 'off'}.
        gain1 (:class:`zhinst.toolkit.control.node_tree.Parameter`): Gain of the 
            output channel 1. The value must be between -1 and +1 (default: +1).
        gain2 (:class:`zhinst.toolkit.control.node_tree.Parameter`): Gain of the 
            output channel 2. The value must be between -1 and +1 (default: +1).

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        super().__init__(parent, index)
        self.output1 = Parameter(
            self,
            dict(
                Node="sigouts/0/on",
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
                Node="sigouts/1/on",
                Description="Enables or disables both ouputs of the AWG. Either can be {'1', '0'} or {'on', 'off'}.",
                Type="Integer",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
            set_parser=Parse.set_on_off,
            get_parser=Parse.get_on_off,
        )
        self.gain1 = Parameter(
            self,
            dict(
                Node="awgs/0/outputs/0/amplitude",
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
                Node="awgs/0/outputs/1/amplitude",
                Description="Sets the gain of the second output channel.",
                Type="Double",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
            set_parser=Parse.amp1,
        )

    def _apply_sequence_settings(self, **kwargs):
        if "sequence_type" in kwargs.keys():
            t = SequenceType(kwargs["sequence_type"])
            allowed_sequences = [
                SequenceType.NONE,
                SequenceType.SIMPLE,
                SequenceType.READOUT,
                SequenceType.CW_SPEC,
                SequenceType.PULSED_SPEC,
                SequenceType.CUSTOM,
            ]
            if t not in allowed_sequences:
                raise ToolkitError(
                    f"Sequence type {t} must be one of {[s.value for s in allowed_sequences]}!"
                )
            # apply settings depending on sequence type
            elif t == SequenceType.CW_SPEC:
                self._apply_cw_settings()
            elif t == SequenceType.PULSED_SPEC:
                self._apply_pulsed_settings()
            elif t == SequenceType.READOUT:
                self._apply_readout_settings()
            else:
                self._apply_base_settings()
        # apply settings dependent on trigger type
        if "trigger_mode" in kwargs.keys():
            if TriggerMode(kwargs["trigger_mode"]) == TriggerMode.EXTERNAL_TRIGGER:
                self._apply_trigger_settings()

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
            ("sigouts/*/enables/*", 0),
            ("sigouts/*/amplitudes/*", 0),
            ("awgs/0/outputs/*/mode", 1),
            ("qas/0/integration/mode", 1),
        ]
        self._parent._set(settings)
        self._parent.disable_readout_channels(range(10))

    def _apply_readout_settings(self):
        settings = [
            ("sigouts/*/enables/*", 0),
            ("awgs/0/outputs/*/mode", 0),
            ("qas/0/integration/mode", 0),
        ]
        self._parent._set(settings)

    def _apply_trigger_settings(self):
        settings = [
            ("/awgs/0/auxtriggers/*/channel", 0),
            ("/awgs/0/auxtriggers/*/slope", 1),
        ]
        self._parent._set(settings)

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
                    raise ToolkitError(
                        "The values should be specified as a tuple, e.g. ('on', 'off')."
                    )
                return self.output1(value[0]), self.output2(value[1])
            else:
                raise ToolkitError("The value must be a tuple or list of length 2!")

    def update_readout_params(self) -> None:
        """Updates the sequence parameters for 'Simple' sequence with values from the readout channels."""
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
                readout_frequencies=freqs, readout_amplitudes=amps, phase_shifts=phases,
            )
        else:
            raise ToolkitError("AWG Sequence type needs to be 'Readout'")

    def compile(self) -> None:
        """Wraps the 'compile(...)' method of the parent class `AWGCore`."""
        if self.sequence_params["sequence_type"] == SequenceType.READOUT:
            self.update_readout_params()
        super().compile()


class ReadoutChannel:
    """Implements a Readout Channel for UHFQA. 

    This class represents the signal processing chain for one of the ten 
    :class:`ReadoutChannels` of a UHFQA. One channel is typically used for 
    dispersive resonator readout of superconducting qubits.

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

    The readout channel can be enabled with `enable()` which means that the 
    weighted integration mode is activated and integration weights are set to 
    demodulate the signal at the given readout frequency. If the channel is 
    enabled, the readout parameters are also used for signal generation in the 
    :class:`AWGCore` if the sequence type is set to *'Readout'*. 

    Attributes:
        index (int): The index of the Readout Channel from 1 - 10.
        rotation (:class:`zhinst.toolkit.control.nodetree.Parameter`): The 
            rotation applied to the signal in IQ plane. The angle is specified 
            in degrees.
        threshold (:class:`zhinst.toolkit.control.nodetree.Parameter`): The 
            signal threshold used for state discrimination in the thresholding 
            unit.
        result (:class:`zhinst.toolkit.control.nodetree.Parameter`): This 
            read-only Parameter holds the result vector for the given readout 
            channel as a 1D numpy array.            

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        if index not in range(10):
            raise ValueError(f"The channel index {index} is out of range!")
        self._index = index
        self._parent = parent
        self._enabled = False
        self._readout_frequency = 100e6
        self._readout_amplitude = 1
        self._phase_shift = 0
        self.rotation = Parameter(
            self,
            dict(
                Node=f"qas/0/rotations/{self._index}",
                Description="Sets the rotation of the readout channel in degrees.",
                Type="Double",
                Properties="Read, Write",
                Unit="Degrees",
            ),
            device=self._parent,
            set_parser=Parse.deg2complex,
            get_parser=Parse.complex2deg,
        )
        self.threshold = Parameter(
            self,
            dict(
                Node=f"qas/0/thresholds/{self._index}/level",
                Description="Sets the threshold of the readout channel.",
                Type="Double",
                Properties="Read, Write",
                Unit="None",
            ),
            device=self._parent,
        )
        self.result = Parameter(
            self,
            dict(
                Node=f"qas/0/result/data/{self._index}/wave",
                Description="Returns the result vector of the readout channel.",
                Type="Numpy array",
                Properties="Read",
                Unit="None",
            ),
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
        """Enables weighted integration for this channel."""
        self._enabled = True
        self._parent._set("qas/0/integration/mode", 0)
        self._parent.integration_time(2e-6)
        self._set_int_weights()

    def disable(self) -> None:
        """Disables weighted integration for this channel."""
        self._enabled = False
        self._reset_int_weights()

    def readout_frequency(self, freq=None):
        """Sets or gets the readout frequency for this channel.
        
        Readout frequency in Hz of the readout channel. If the AWG 
        :class:`SequenceProgram` is of type "Readout", this Parameter is used to 
        generate a readout tone at the given readout frequency for all readout 
        channels that are enabled. This frequency is also used in the signal 
        acquisition for digital demodulation if the readout channel is 
        enabled. The frequency must be positive.
        
        """
        if freq is None:
            return self._readout_frequency
        else:
            Parse.greater0(freq)
            self._readout_frequency = freq
            self._set_int_weights()
            return self._readout_frequency

    def readout_amplitude(self, amp=None):
        """Sets or gets the readout amplitude for this channel.
        
        The amplitude of the readout pulse is used for signal generation of the 
        readout tone if the channel is enabled and if the AWG 
        :class:`SequenceProgram` is of type *'Readout'*. (default: 1.0)
        
        """
        if amp is None:
            return self._readout_amplitude
        else:
            Parse.amp1(amp)
            self._readout_amplitude = amp
            return self._readout_amplitude

    def phase_shift(self, ph=None):
        """Sets or gets the readout phase shift for this channel.
        
        Additional phase shift in the signal generation between I and Q 
        quadtratures. (default: 0)
        
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
        l = self._parent._get("qas/0/integration/length")
        freq = self.readout_frequency()
        node = f"/qas/0/integration/weights/{self._index}/"
        self._parent._set(node + "real", self._demod_weights(l, freq, 0))
        self._parent._set(node + "imag", self._demod_weights(l, freq, 90))

    def _demod_weights(self, length, freq, phase):
        if length > 4096:
            raise ValueError(
                "The maximum length of the integration weights is 4096 samples."
            )
        if freq <= 0:
            raise ValueError("This frequency must be positive.")
        clk_rate = 1.8e9
        x = np.arange(0, length)
        y = np.sin(2 * np.pi * freq * x / clk_rate + np.deg2rad(phase))
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
