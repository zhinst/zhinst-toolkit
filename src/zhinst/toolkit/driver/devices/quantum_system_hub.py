"""PQSC and QHub base Instrument Driver."""

import logging
import time
from typing import List, Union

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.exceptions import ToolkitError


logger = logging.getLogger(__name__)


class QuantumSystemHub(BaseInstrument):
    """Base driver for the Zurich Instruments PQSC and QHub.

    This class should not be instantiated directly, but instead through
    PQSC or QHub
    """

    def run(self, *, deep: bool = True) -> None:
        """Start sending out triggers.

        This method activates the trigger generation to trigger all
        connected instruments over ZSync ports.

        Args:
            deep: A flag that specifies if a synchronization
                should be performed between the device and the data
                server after enabling the PQSC/QHub (default: True).

        """
        self.execution.enable(True, deep=deep)

    def arm_and_run(self, *, repetitions: int = None, holdoff: float = None) -> None:
        """Arm the PQSC/QHub and start sending out triggers.

        Simply combines the methods arm and run. A synchronization
        is performed between the device and the data server after
        arming and running the PQSC/QHub.

        Args:
            repetitions: If specified, the number of triggers sent
                over ZSync ports will be set (default: None).
            holdoff: If specified, the time between repeated
                triggers sent over ZSync ports will be set. It has a
                minimum value and a granularity of 100 ns
                (default: None).

        """
        self.arm(deep=True, repetitions=repetitions, holdoff=holdoff)
        self.run(deep=True)

    def stop(self, *, deep: bool = True) -> None:
        """Stop the trigger generation.

        Args:
            deep: A flag that specifies if a synchronization
                should be performed between the device and the data
                server after disabling the PQSC/QHub (default: True).

        """
        self.execution.enable(False, deep=deep)

    def wait_done(self, *, timeout: float = 10.0, sleep_time: float = 0.005) -> None:
        """Wait until trigger generation and feedback processing is done.

        Args:
            timeout: The maximum waiting time in seconds for the
                PQSC/QHub (default: 10.0).
            sleep_time: Time in seconds to wait between
                requesting PQSC/QHub state

        Raises:
            TimeoutError: If the PQSC/QHub is not done sending out all
                triggers and processing feedback before the timeout.
        """
        try:
            self.execution.enable.wait_for_state_change(
                0, timeout=timeout, sleep_time=sleep_time
            )
        except TimeoutError as error:
            raise TimeoutError(f"{self.__class__.__name__:s} timed out.") from error

    def check_ref_clock(
        self, *, timeout: float = 30.0, sleep_time: float = 1.0
    ) -> bool:
        """Check if reference clock is locked successfully.

        Args:
            timeout: Maximum time in seconds the program waits
                (default: 30.0).
            sleep_time: Time in seconds to wait between
                requesting the reference clock status (default: 1)

        Raises:
            TimeoutError: If the process of locking to the reference clock
                exceeds the specified timeout.
        """
        ref_clock_status = self.system.clocks.referenceclock.in_.status
        ref_clock = self.system.clocks.referenceclock.in_.source
        ref_clock_actual = self.system.clocks.referenceclock.in_.sourceactual
        try:
            ref_clock_status.wait_for_state_change(
                2, invert=True, timeout=timeout, sleep_time=sleep_time
            )
        except TimeoutError as error:
            raise TimeoutError(
                "Timeout during locking to reference clock signal"
            ) from error
        if ref_clock_status() == 0:
            return True
        if ref_clock_status() == 1 and ref_clock_actual() != ref_clock():
            ref_clock("internal", deep=True)
            logger.error(
                f"There was an error locking the device({self.serial}) "
                f"onto reference clock signal. Automatically switching to internal "
                f"reference clock. Please try again."
            )
        return False

    def check_zsync_connection(
        self,
        inputs: Union[List[int], int, List[BaseInstrument], BaseInstrument],
        *,
        timeout: float = 10.0,
        sleep_time: float = 0.1,
    ) -> Union[List[bool], bool]:
        """Check if a ZSync connection is established.

        Checks the current status of the instrument connected to the given ports.
        If a instrument(s) is given instead of a port number, first finds the correct
        port number(s).

        Args:
            inputs: The port numbers to check the ZSync connection for.
                It can either be a single port number given as integer, a list
                of several port numbers an instrument or a list of instruments.
            timeout: Maximum time in seconds the program waits (default: 10.0).
            sleep_time: Time in seconds to wait between requesting the reference
                clock status (default: 0.1)

            .. versionchanged:: 0.6.1: Reduce default timeout and sleep_time.
            .. versionchanged:: 0.6.1: Raise an error if the port is in a faulty
                                       state, instead of return False.


        Raises:
            TimeoutError: If the process of establishing a ZSync connection on
                one of the specified ports exceeds the specified timeout.
        """
        inputs_list = inputs if isinstance(inputs, list) else [inputs]

        start_time = time.time()

        # Check the status of all ports
        status = []
        for input in inputs_list:
            # Convert the instrument into a port, if needed
            if isinstance(input, BaseInstrument):
                port = self.find_zsync_worker_port(
                    input,
                    timeout=max(0, timeout - (time.time() - start_time)),
                    sleep_time=sleep_time,
                )
            else:
                port = input

            # Check or wait until the connection is ready
            status.append(
                self._check_zsync_connection(
                    port,
                    timeout=max(0, timeout - (time.time() - start_time)),
                    sleep_time=sleep_time,
                )
            )
        return status if isinstance(inputs, list) else status[0]

    def _check_zsync_connection(
        self, port: int, timeout: float, sleep_time: float
    ) -> bool:
        """Check if the ZSync connection on the given port is successful.

        This function checks the current status of the instrument
        connected to the given port.

        Args:
            ports: Port number to check the ZSync connection for.
            timeout: Maximum time in seconds the program waits.
            sleep_time: Time in seconds to wait between requesting the status

        Raises:
            TimeoutError: If the process of establishing a ZSync connection the
                specified port exceeds the specified timeout.
        """
        status_node = self.zsyncs[port].connection.status
        try:
            # Waits until the status node is "connected" (2)
            status_node.wait_for_state_change(2, timeout=timeout, sleep_time=sleep_time)
        except TimeoutError as error:
            status = status_node()
            err_msg = (
                "Timeout while establishing ZSync connection to the instrument "
                f"on the port {port}."
            )

            if status == 0:
                # No connection
                err_msg += "No instrument detected."
            elif status == 1:
                # In progress
                err_msg += (
                    "Connection still in progress. Consider increasing the timeout."
                )
            elif status == 3:
                # Error
                err_msg += (
                    "Impossible to establish a connect. Check cabling and FW version"
                )

            raise TimeoutError(err_msg) from error
        return True

    def find_zsync_worker_port(
        self,
        device: BaseInstrument,
        timeout: float = 10.0,
        sleep_time: float = 0.1,
    ) -> int:
        """Find the ID of the PQSC/QHub ZSync port connected to a given device.

        The function checks until the given timeout for the specified device to
        show up in the connection list.

        Args:
            device: device for which the connected ZSync port shall be found.
            timeout: Maximum time in seconds the program waits (default: 10.0).
            sleep_time: Time in seconds to wait between requesting the port
                serials list (default: 0.1)

            .. versionchanged:: 0.6.1: Added timeout and sleep_time parameters.

        Returns:
            Index of the searched PQSC/QHub ZSync port.

        Raises:
            ToolkitError: If the given device doesn't appear to be connected
                to the PQSC/QHub via ZSync.

        .. versionadded:: 0.5.1
        """
        device_serial = device.serial[3:]

        start = time.time()
        while time.time() - start < timeout:
            node_to_serial_dict = self.zsyncs["*"].connection.serial()

            if device_serial in node_to_serial_dict.values():
                break

            time.sleep(sleep_time)
        else:
            raise ToolkitError(
                f"No ZSync connection found between {self.__class__.__name__:s}"
                f"{self.serial:s} and the device {device.serial:s}."
            )

        # Get the node of the ZSync connected to the device
        # (will have the form "/devXXXX/zsyncs/N/connection/serial")
        serial_to_node_dict = {
            serial: node for node, serial in node_to_serial_dict.items()
        }
        device_zsync_node = serial_to_node_dict[device_serial]

        # Just interested in knowing N: split in
        # ['', 'devXXXX', 'zsyncs', 'N', 'connection', 'serial']
        # and take fourth value
        return int(device_zsync_node.split("/")[3])
