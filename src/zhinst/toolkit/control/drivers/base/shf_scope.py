# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from .base import BaseInstrument, ToolkitError


class SHFScope:
    """Implements a Scope representation.

    The :class:`SHFScope` class implements basic functionality of
    the SHF Scope.
    """

    def __init__(self, parent: BaseInstrument) -> None:
        self._parent = parent

    def _init_scope_params(self):
        """Initialize parameters associated with device scope.

        Can be overwritten by any Scope that inherits from the
        :class:`SHFScope`.

        """
        pass

    def run(self) -> None:
        """Runs the scope recording."""
        self.enable(1)

    def stop(self) -> None:
        """Stops the scope recording."""
        self.enable(0)

    def read(self, channel=None):
        """Read out the recorded data from the specified channel of the scope.

        Arguments:
            channel (int): The scope channel to read the data from. If
                no channel is specified, the method will return the data
                for all channels.

        Returns:
            A dictionary showing the recorded data and scope time.
        """

        # wait until scope has been triggered, 30s timeout
        tik = time.time()
        while self.enable() != 0:
            time.sleep(0.1)
            if time.time() - tik >= 30:
                raise ToolkitError("Scope recording timed out!")
        # read and post-process the recorded data
        recorded_data = [[], [], [], []]
        num_channels = self._parent._num_channels()
        # generate the wave data
        for i in range(num_channels):
            channel_state = getattr(self, f"channel{i+1}")
            wave_data = getattr(self, f"wave{i+1}")
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

        Keyword Arguments:
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
                    raise ToolkitError(
                        "The values should be specified as a tuple or list, e.g. ('on', 'off', 'off', 'off')."
                    )
                self.channel1(value[0])
                self.channel2(value[1])
                self.channel3(value[2])
                self.channel4(value[3])
            else:
                raise ToolkitError("The value must be a tuple or list of length 4!")

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
                    raise ToolkitError(
                        "The values should be specified as a tuple or list, e.g. "
                        "('chan0sigin', 'chan1sigin', 'chan2sigin', 'chan3sigin')."
                    )
                self.input_select1(value[0])
                self.input_select2(value[1])
                self.input_select3(value[2])
                self.input_select4(value[3])
            else:
                raise ToolkitError("The value must be a tuple or list of length 4!")

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
            self.segments_count(count)
        if enable is not None:
            self.segments_enable(enable)
        return {"Enable": self.segments_enable(), "Segments": self.segments_count()}

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
            self.averaging_count(count)
        if enable is not None:
            self.averaging_enable(enable)
        return {
            "Enable": self.averaging_enable(),
            "Averages": self.averaging_count(),
        }
