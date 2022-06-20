"""PQSC Instrument Driver."""

import logging
import time
from typing import List, Union

from zhinst.toolkit.driver.devices.base import BaseInstrument

logger = logging.getLogger(__name__)


class PQSC(BaseInstrument):
    """High-level driver for the Zurich Instruments PQSC."""

    def arm(self, *, deep=True, repetitions: int = None, holdoff: float = None) -> None:
        """Prepare PQSC for triggering the instruments.

        This method configures the execution engine of the PQSC and
        clears the register bank. Optionally, the *number of triggers*
        and *hold-off time* can be set when specified as keyword
        arguments. If they are not specified, they are not changed.

        Note that the PQSC is disabled at the end of the hold-off time
        after sending out the last trigger. Therefore, the hold-off time
        should be long enough such that the PQSC is still enabled when
        the feedback arrives. Otherwise, the feedback cannot be processed.

        Args:
            deep: A flag that specifies if a synchronization
                should be performed between the device and the data
                server after stopping the PQSC and clearing the
                register bank (default: True).
            repetitions: If specified, the number of triggers sent
                over ZSync ports will be set (default: None).
            holdoff: If specified, the time between repeated
                triggers sent over ZSync ports will be set. It has a
                minimum value and a granularity of 100 ns
                (default: None).

        """
        # Stop the PQSC if it is already running
        self.stop(deep=deep)
        if repetitions is not None:
            self.execution.repetitions(repetitions)
        if holdoff is not None:
            self.execution.holdoff(holdoff)
        # Clear register bank
        self.feedback.registerbank.reset(1, deep=deep)

    def run(self, *, deep: bool = True) -> None:
        """Start sending out triggers.

        This method activates the trigger generation to trigger all
        connected instruments over ZSync ports.

        Args:
            deep: A flag that specifies if a synchronization
                should be performed between the device and the data
                server after enabling the PQSC (default: True).

        """
        self.execution.enable(True, deep=deep)

    def arm_and_run(self, *, repetitions: int = None, holdoff: float = None) -> None:
        """Arm the PQSC and start sending out triggers.

        Simply combines the methods arm and run. A synchronization
        is performed between the device and the data server after
        arming and running the PQSC.

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
                server after disabling the PQSC (default: True).

        """
        self.execution.enable(False, deep=deep)

    def wait_done(self, *, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until trigger generation and feedback processing is done.

        Args:
            timeout: The maximum waiting time in seconds for the
                PQSC (default: 10).
            sleep_time: Time in seconds to wait between
                requesting PQSC state

        Raises:
            TimeoutError: If the PQSC is not done sending out all
                triggers and processing feedback before the timeout.
        """
        try:
            self.execution.enable.wait_for_state_change(
                0, timeout=timeout, sleep_time=sleep_time
            )
        except TimeoutError as error:
            raise TimeoutError("PQSC timed out.") from error

    def check_ref_clock(self, *, timeout: int = 30, sleep_time: int = 1) -> bool:
        """Check if reference clock is locked successfully.

        Args:
            timeout: Maximum time in seconds the program waits
                (default: 30).
            sleep_time: Time in seconds to wait between
                requesting the reference clock status (default: 1)

        Raises:
            ToolkitError: If the process of locking to the reference clock
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
        ports: Union[List[int], int] = 0,
        *,
        timeout: int = 30,
        sleep_time: int = 1,
    ) -> Union[List[bool], bool]:
        """Check if the ZSync connection on the given port(s) is established.

        This function checks the current status of the instrument connected to
        the given ports.

        Args:
            ports: The port numbers to check the ZSync connection for.
                It can either be a single port number given as integer or a list
                of several port numbers. (default: 0)
            timeout: Maximum time in seconds the program waits (default: 30).
            sleep_time: Time in seconds to wait between requesting the reference
                clock status (default: 1)

        Raises:
            TimeoutError: If the process of establishing a ZSync connection on
                one of the specified ports exceeds the specified timeout.
        """
        ports_list = ports if isinstance(ports, list) else [ports]

        start_time = time.time()
        status = []
        for port in ports_list:
            status.append(
                self._check_zsync_connection(
                    port,
                    timeout=max(0, timeout - (time.time() - start_time)),
                    sleep_time=sleep_time,
                )
            )
        return status if isinstance(ports, list) else status[0]

    def _check_zsync_connection(
        self, port: int, timeout: float, sleep_time: float
    ) -> bool:
        """Check if the ZSync connection on the given port is successful.

        This function checks the current status of the instrument
        connected to the given port.

        Args:
            ports: Port number to check the ZSync connection for.
            timeout: Maximum time in seconds the program waits (default: 30).
            sleep_time: Time in seconds to wait between requesting the status
                (default: 1)

        Raises:
            TimeoutError: If the process of establishing a ZSync connection the
                specified port exceeds the specified timeout.
        """
        status_node = self.zsyncs[port].connection.status
        start_time = time.time()
        try:
            status_node.wait_for_state_change(
                0, invert=True, timeout=timeout, sleep_time=sleep_time
            )
            status_node.wait_for_state_change(
                1,
                invert=True,
                timeout=max(0, timeout - (time.time() - start_time)),
                sleep_time=sleep_time,
            )
        except TimeoutError as error:
            raise TimeoutError(
                "Timeout while establishing ZSync connection to the instrument "
                f"on the port {port}."
            ) from error
        return status_node() == 2
