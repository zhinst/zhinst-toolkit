"""SHF* Instrument Driver."""

import logging

from zhinst.toolkit.driver.devices.base import BaseInstrument

logger = logging.getLogger(__name__)


class SHF(BaseInstrument):
    """Class for SHF*-common functionality."""

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
