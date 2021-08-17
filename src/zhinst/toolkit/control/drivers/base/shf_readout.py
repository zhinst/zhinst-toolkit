# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import time

from zhinst.toolkit.interface import LoggerModule
from .shf_qachannel import SHFQAChannel

_logger = LoggerModule(__name__)


class SHFReadout:
    """Implements an SHF Readout module representation.

    The :class:`SHFReadout` class implements basic readout functionality
    of the SHF device allowing the user to realize qubit measurements.

    Attributes:
        parent (:class:`SHFQAChannel`): The parent qachannel that this
            :class:`SHFGenerator` is associated to.
        device (:class:`BaseInstrument`): The instrument that this
            :class:`SHFGenerator` is associated to.
        index (int): An integer specifying the index in the instrument.
        is_running (bool): A flag that shows if the `SHFGenerator` is
            currently running or not.

    """

    def __init__(self, parent: SHFQAChannel) -> None:
        self._parent = parent
        self._index = self._parent._index
        self._device = self._parent._parent

    def _init_readout_params(self):
        """Initialize parameters associated with the readout
        functionality of the device.

        Can be overwritten by any Readout module that inherits from the
        :class:`SHFReadout`.

        """
        pass

    @property
    def parent(self):
        return self._parent

    @property
    def device(self):
        return self._device

    @property
    def index(self):
        return self._index

    @property
    def is_running(self):
        return self._enable()

    def arm(self, sync=True, length: int = None, averages: int = None) -> None:
        """Prepare SHF device for readout and result acquisition.

        This method enables the QA Results Acquisition and resets the
        acquired points. Optionally, the *result length* and
        *result averages* can be set when specified as keyword
        arguments. If they are not specified, they are not changed.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after stopping the SHF device and clearing the
                register bank (default: True).
            length (int): If specified, the length of the result vector
                will be set before arming the readout.
                (default: None)
            averages (int): If specified, the result averages will be
                set before arming the readout. (default: None)

        """
        # Stop the result logger to reset it
        # if some old measurement is still running
        self.stop(sync=sync)
        if length is not None:
            self.result_length(length)
        if averages is not None:
            self.num_averages(averages)
        # Start the result logger again
        self.run(sync=sync)

    def run(self, sync=True) -> None:
        """Start the result logger.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after starting the result logger (default: True).

        Raises:
            ToolkitError: If `sync=True` and the result logger cannot
                be started

        """
        self._enable(True, sync=sync)
        if sync and not self._enable.assert_value(True):
            _logger.error(
                f"There was an error while starting the result logger. This can "
                f"happen if an already running result logger is stopped by the "
                f"user and started again immediately. Please make sure that the "
                f"result logger has actually stopped before trying to start it "
                f"again.",
                _logger.ExceptionTypes.ToolkitError,
            )

    def stop(self, sync=True) -> None:
        """Stop the result logger.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after stopping the result logger (default: True).

        Raises:
            ToolkitError: If `sync=True` and the result logger cannot
                be stopped

        """
        self._enable(False, sync=sync)
        if sync and not self._enable.assert_value(False):
            _logger.error(
                f"There was an error while stopping the result logger. This can "
                f"happen if the result logger is started by the user and stopped "
                f"again immediately. Please make sure that the result logger has "
                f"actually started before trying to stop it again.",
                _logger.ExceptionTypes.ToolkitError,
            )

    def wait_done(self, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until readout is finished.

        Arguments:
            timeout (float): The maximum waiting time in seconds for the
                Readout (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting Readout state

        Raises:
            TimeoutError: if the readout recording is not completed
                before timeout.

        """
        start_time = time.time()
        while self.is_running and start_time + timeout >= time.time():
            time.sleep(sleep_time)
        if self.is_running and start_time + timeout < time.time():
            _logger.error(
                "Readout timed out!",
                _logger.ExceptionTypes.TimeoutError,
            )

    def read(
        self,
        integrations: list = [],
        blocking: bool = True,
        timeout: float = 10,
        sleep_time: float = 0.005,
    ):
        """Read out the measured data from the result logger.

        Arguments:
            integrations (list): The list of integrations to return the
                data for. If no integration is specified, the method
                will return the data for all integrations
                (default: []).
            blocking (bool): A flag that specifies if the program
                should be blocked until the result logger finished
                recording (default: True).
            timeout (float): The maximum waiting time in seconds for the
                Readout (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting Readout state

        Returns:
            An array containing the result logger data.

        Raises:
            TimeoutError: if the readout recording is not completed
                before timeout.

        """
        num_integrations = self._device.num_integrations_per_qachannel()
        if blocking:
            # Wait until result logger has finished recording
            self.wait_done(timeout=timeout, sleep_time=sleep_time)
        # read the measurement data
        result = []
        for j in range(num_integrations):
            result.append(self.integrations[j].result())
        # decide what to return
        if not integrations:
            return result
        else:
            return [result[i] for i in integrations]
