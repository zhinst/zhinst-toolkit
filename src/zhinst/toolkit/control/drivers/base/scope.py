# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from .base import BaseInstrument
from zhinst.toolkit.interface import LoggerModule
from ...parsers import Parse

_logger = LoggerModule(__name__)


class Scope:
    """Implements a Scope representation.

    The :class:`Scope` class implements basic functionality of
    the Scope for UHF devices.

    """

    def __init__(self, parent: BaseInstrument) -> None:
        self._parent = parent
        self._module = None

    def _setup(self):
        self._module = self._parent._controller.connection.scope_module

    def _init_scope_settings(self):
        if self._module is None:
            _logger.error(
                "This Scope is not connected to a scopeModule!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        # Set scope data processing mode to `time`
        self.mode("time")
        # Set number of records to 1
        self.num_records(1)
        # Set the averager weight to 1
        self.averager_weight(1)

    def _init_scope_params(self):
        """Initialize parameters associated with device scope.

        Can be overwritten by any Scope that inherits from the
        :class:`Scope`.

        """
        pass

    def arm(
        self, sync=True, num_records: int = None, averager_weight: int = None
    ) -> None:
        """Prepare the scope for recording.

        This method tells the scope module to be ready to acquire data
        and resets the scope module's progress to 0.0. Optionally, the
        *number of records* and *averager weight* can be set when
        specified as keyword argument. If it is not specified, it is not
        changed.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after preparing scope (default: True).
            num_records (int): The number of scope records to acquire
                (default: None).
            averager_weight (int): Averager weight parameter.
                Averaging is disabled if it is set to 1. For values
                greater than 1, the scope  record shots are averaged
                using an exponentially weighted moving average
                (default: None).

        """
        if self._module is None:
            _logger.error(
                "This Scope is not connected to a scopeModule!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        # Stop the Scope if it is already running
        self.stop(sync=sync)
        # Set history length to number of records
        if num_records is not None:
            self.num_records(num_records)
        # Set the averager weight
        if averager_weight is not None:
            self.averager_weight(averager_weight)
        # Enable continuous scope recording if number of records is
        # greater than 1
        if self.num_records() > 1 and self.single():
            self.single(False, sync=sync)
            # Issue a warning to inform the user
            _logger.warning(
                f"Number of recordings is set to {self.num_records()}. The scope must "
                f"run in continuous mode. Disabling single mode automatically. ",
            )
        # Subscribe to the scope's data in the module
        self._module.update_device(self._parent.serial)
        # Tell the module to be ready to acquire data;
        # reset the module's progress to 0.0.
        self._module.execute()

    def run(self, sync=True) -> None:
        """Run the scope recording.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after enabling the scope (default: True).

        """
        # Enable the scope:
        # Now the scope is ready to record data upon receiving triggers.
        self._enable(True, sync=sync)

    def arm_and_run(self, num_records: int = None, averager_weight: int = None) -> None:
        """Arm the scope and start recording

        Simply combines the methods arm and run. A synchronisation
        is performed between the device and the data server after
        preparing scope.

        Arguments:
            num_records (int): The number of scope records to acquire
                (default: None).
            averager_weight (int): Averager weight parameter.
                Averaging is disabled if it is set to 1. For values
                greater than 1, the scope  record shots are averaged
                using an exponentially weighted moving average
                (default: None).

        """
        self.arm(sync=True, num_records=num_records, averager_weight=averager_weight)
        self.run(sync=True)

    def stop(self, sync=True) -> None:
        """Stops the scope recording.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after disabling the scope (default: True).

        """
        self._enable(False, sync=sync)
        # Stop the module; to use it again we need to call execute().
        self._module.finish()

    def wait_done(self, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the Scope recording is finished.

        Arguments:
            timeout (float): The maximum waiting time in seconds for the
                Scope (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting the progress and records values

        Raises:
            TimeoutError: If the Scope recording is not done before the
                timeout.

        """
        num_records = self.num_records()
        start_time = time.time()
        records = 0
        progress = 0
        # Wait until the Scope Module has received and
        # processed the desired number of records.
        while (
            records < num_records or progress < 1.0
        ) and start_time + timeout >= time.time():
            time.sleep(sleep_time)
            records = self._module.records()
            progress = self._module.progress()
        if (
            records < num_records or progress < 1.0
        ) and start_time + timeout < time.time():
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
                for all channels (default: None).
            blocking (bool): A flag that specifies if the program
                should be blocked until the Scope Module has received
                and  processed the desired number of records
                (default: True).
            timeout (float): The maximum waiting time in seconds for the
                Scope (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting the progress and records values

        Raises:
            TimeoutError: If the Scope recording is not done before the
                timeout.

        Returns:
            A dictionary showing the recorded data and scope time.
            
        """
        num_records = self.num_records()
        wave_nodepath = f"/{self._parent.serial}/scopes/0/wave"
        if blocking:
            # Wait until the Scope Module has received and
            # processed the desired number of records.
            self.wait_done(timeout=timeout, sleep_time=sleep_time)
        # Stop the scope
        self.stop()
        # read and post-process the recorded data
        result = []
        # generate the wave data
        channel_states = self.channels()
        data = self._module.read()
        for j in range(num_records):
            recorded_data = [[], []]
            wave_data = data[wave_nodepath][j][0]["wave"]
            dt = data[wave_nodepath][j][0]["dt"]
            for i in range(2):
                if channel_states[i] == "on":
                    recorded_data[i] = wave_data[i]
            # generate the time base
            scope_time = [[], []]
            for i in range(2):
                scope_time[i] = np.array(range(0, len(recorded_data[i]))) * dt
            # return the scope data
            if channel is not None:
                result.append(
                    {"data": recorded_data[channel], "time": scope_time[channel]}
                )
            else:
                result.append({"data": recorded_data, "time": scope_time})
        return result

    def channels(self, value=None):
        """Set all Scope channels simultaneously.

        Arguments:
            value (tuple): Tuple of values {'on', 'off'} for channel 1
                and 2 (default: None).

        Returns:
            A tuple with the states {'on', 'off'} for all input channels.

        """
        if value is None:
            # Read the channel states and convert the result to
            # inverse binary string
            binary_states = format(self._channel(), "02b")[::-1]
            # Generate tuple from the string (character-wise)
            channel_states = tuple([int(state) for state in binary_states])
            # Returned the parsed tuple
            return Parse.get_on_off_tuple_list(channel_states, 2)
        else:
            channel_states = Parse.set_on_off_tuple_list(value, 2)
            # Generate inverse binary string from list or tuple
            binary_states = "".join(map(str, channel_states))[::-1]
            value = int(binary_states, 2)
            if value == 0:
                _logger.error(
                    "At least one scope channel must be active.",
                    _logger.ExceptionTypes.ValueError,
                )
            self._channel(value)

    def mode(self, value=None):
        """Set or get scope data processing mode.

        Arguments:
            value (str): Can be either "time" or "FFT" (default: None).

        Returns:
            If no argument is given the method returns the current
            scope data processing mode.

        """
        return self._module.mode(mode=value)

    def num_records(self, value=None):
        """Set or get the number of scope records to acquire.

        Arguments:
            value (int): The number of scope records to acquire
                (default: None).

        Returns:
            If no argument is given the method returns the current
            number of scope records to acquire.

        """
        return self._module.historylength(length=value)

    def averager_weight(self, value=None):
        """Set or get the averager weight parameter.

        Arguments:
            value (int): Averager weight parameter. Averaging is
                disabled if it is set to 1. For values greater than 1,
                the scope record shots are averaged using an
                exponentially weighted moving average (default: None).

        Returns:
            If no argument is given the method returns the current
            scope data processing mode.

        """
        return self._module.averager_weight(weight=value)

    @property
    def is_running(self):
        return self._enable()
