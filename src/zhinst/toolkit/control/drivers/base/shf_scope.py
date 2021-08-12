# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from .base import BaseInstrument
from zhinst.toolkit.interface import LoggerModule

_logger = LoggerModule(__name__)


class SHFScope:
    """Implements a Scope representation.

    The :class:`SHFScope` class implements basic functionality of
    the SHF Scope.

    For example, the scope can be configured like this to record the
    signal at channel 1:

        >>> scope = shf.scope
        >>> scope.channels(["on", "off", "off", "off"])
        >>> scope.input_select(["chan0sigin", "chan1sigin", "chan2sigin", "chan3sigin"])
        >>> scope.segments(enable = False, count=1)
        >>> scope.averaging(enable = False, count=1)
        >>> scope.length(12512)
        >>> scope.time(0)

    To start recording and obtain the result:

        >>> scope.run()
        >>> result = scope.read(0)
    """

    def __init__(self, parent: BaseInstrument) -> None:
        self._parent = parent

    def _init_scope_params(self):
        """Initialize parameters associated with device scope.

        Can be overwritten by any Scope that inherits from the
        :class:`SHFScope`.

        """
        pass

    def run(self, sync=True) -> None:
        """Run the scope recording.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after starting the scope recording
                (default: True).

        """
        self._enable(True, sync=sync)

    def stop(self, sync=True) -> None:
        """Stop the scope recording.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after stopping scope recording
                (default: True).

        """
        self._enable(False, sync=sync)

    def wait_done(self, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the Scope recording is finished.

        Arguments:
            timeout (int): The maximum waiting time in seconds for the
                Scope (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting the progress and records values

        Raises:
            ToolkitError: If the Scope recording is not done before the
                timeout.

        """
        start_time = time.time()
        while self.is_running and start_time + timeout >= time.time():
            time.sleep(sleep_time)
        if self.is_running and start_time + timeout < time.time():
            _logger.error(
                "Scope recording timed out!",
                _logger.ExceptionTypes.TimeoutError,
            )

    def read(
        self,
        channel=None,
        blocking: bool = True,
        timeout: float = 10,
        sleep_time: float = 0.005,
    ):
        """Read out the recorded data from the specified channel of the scope.

        Arguments:
            channel (int): The scope channel to read the data from. If
                no channel is specified, the method will return the data
                for all channels.
            blocking (bool): A flag that specifies if the program
                should be blocked until the scope has finished
                recording (default: True).
            timeout (float): The maximum waiting time in seconds for the
                Scope (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting the progress and records values

        Returns:
            A dictionary showing the recorded data and scope time.

        Raises:
            TimeoutError: if the scope recording is not completed before
                timeout.

        """
        if blocking:
            # Wait until scope has finished recording
            self.wait_done(timeout=timeout, sleep_time=sleep_time)
        # read and post-process the recorded data
        recorded_data = [[], [], [], []]
        num_channels = self._parent.num_qachannels()
        # generate the wave data
        for i in range(num_channels):
            channel_state = getattr(self, f"channel{i+1}")
            wave_data = getattr(self, f"_wave{i+1}")
            if channel_state() == "on":
                recorded_data[i] = wave_data()
        # generate the time base
        scope_time = [[], [], [], []]
        sampling_frequency = 2e9
        for key, value in self.time._map.items():
            if value == self.time():
                decimation_rate = 2 ** int(key)
        sampling_rate = sampling_frequency / decimation_rate  # [Hz]
        for i in range(num_channels):
            scope_time[i] = np.array(range(0, len(recorded_data[i]))) / sampling_rate
        # return the scope data
        if channel is not None:
            result = {
                "data": recorded_data[channel],
                "time": scope_time[channel],
            }
        else:
            result = {
                "data": recorded_data,
                "time": scope_time,
            }
        return result

    def channels(self, value=None):
        """Set all Scope channels simultaneously.

        Arguments:
            value (tuple): Tuple of values {'on', 'off'} for channel 1,
                2, 3 and 4 (default: None).

        Returns:
            A tuple with the states {'on', 'off'} for all input channels.

        """
        if value is None:
            return self.channel1(), self.channel2(), self.channel3(), self.channel4()
        else:
            if isinstance(value, tuple) or isinstance(value, list):
                if len(value) != 4:
                    _logger.error(
                        "The values should be specified as a tuple or list, "
                        "e.g. ('on', 'off', 'off', 'off').",
                        _logger.ExceptionTypes.ToolkitError,
                    )
                self.channel1(value[0])
                self.channel2(value[1])
                self.channel3(value[2])
                self.channel4(value[3])
            else:
                _logger.error(
                    "The value must be a tuple or list of length 4!",
                    _logger.ExceptionTypes.ToolkitError,
                )

    def input_select(self, value=None):
        """Set all Scope input signals simultaneously.

        Keyword Arguments:
            value (tuple): Tuple of values for input signal 1,
                2, 3 and 4. The accepted values can be found in SHFQA
                user manual (default: None).

        Returns:
            A tuple with the selected input signal sources for all
            input channels.

        """
        if value is None:
            return (
                self.input_select1(),
                self.input_select2(),
                self.input_select3(),
                self.input_select4(),
            )
        else:
            if isinstance(value, tuple) or isinstance(value, list):
                if len(value) != 4:
                    _logger.error(
                        "The values should be specified as a tuple or list, e.g. "
                        "('chan0sigin', 'chan1sigin', 'chan2sigin', 'chan3sigin').",
                        _logger.ExceptionTypes.ToolkitError,
                    )
                self.input_select1(value[0])
                self.input_select2(value[1])
                self.input_select3(value[2])
                self.input_select4(value[3])
            else:
                _logger.error(
                    "The value must be a tuple or list of length 4!",
                    _logger.ExceptionTypes.ToolkitError,
                )

    def segments(self, enable=None, count=None):
        """Configure segmented Scope recording options.

        Keyword Arguments:
            enable (bool): a flag that specifies whether segmented Scope
                recording is enabled (default: None).
            count (int): number of segments in device memory (default: None)

        Returns:
            A dictionary showing the enable state and segment count

        """
        if count is not None:
            self._segments_count(count)
        if enable is not None:
            self._segments_enable(enable)
        return {"Enable": self._segments_enable(), "Segments": self._segments_count()}

    def averaging(self, enable=None, count=None):
        """Configure averaging options of Scope measurements.

        Keyword Arguments:
            enable (bool): a flag that specifies whether averaging of
                Scope measurements is enabled (default: None).
            count (int): number of Scope measurements to average
                (default: None)

        Returns:
            A dictionary showing the enable state and averaging count
            
        """
        if count is not None:
            self._averaging_count(count)
        if enable is not None:
            self._averaging_enable(enable)
        return {
            "Enable": self._averaging_enable(),
            "Averages": self._averaging_count(),
        }

    @property
    def is_running(self):
        return self._enable()
