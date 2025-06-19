"""SHF* Instrument Driver."""

import logging
import time
from itertools import chain

from zhinst.toolkit.driver.devices.base import BaseInstrument

logger = logging.getLogger(__name__)


class SHF(BaseInstrument):
    """Class for SHF*-common functionality."""

    def check_ref_clock(
        self,
        *,
        timeout: float = 30.0,
        sleep_time: float = 1.0,
    ) -> bool:
        """Check if reference clock is locked successfully.

        Args:
            timeout: Maximum time in seconds the program waits
                (default: 30.0).
            sleep_time: Time in seconds to wait between
                requesting the reference clock status (default: 1.0)

        Raises:
            TimeoutError: If the process of locking to the reference clock
                exceeds the specified timeout.
        """
        ref_clock_status = self.system.clocks.referenceclock.in_.status
        locked_enum = ref_clock_status.node_info.enum.locked
        busy_enum = ref_clock_status.node_info.enum.busy

        ref_clock = self.system.clocks.referenceclock.in_.source
        ref_clock_actual = self.system.clocks.referenceclock.in_.sourceactual
        try:
            ref_clock_status.wait_for_state_change(
                busy_enum,
                invert=True,
                timeout=timeout,
                sleep_time=sleep_time,
            )
        except TimeoutError as error:
            msg = "Timeout during locking to reference clock signal"
            raise TimeoutError(
                msg,
            ) from error
        if ref_clock_status() == locked_enum and ref_clock_actual() == ref_clock():
            timeout = 5.0
            start_time = time.time()
            for channel in chain(self.qachannels, self.sgchannels):
                remaining_timeout = timeout - (time.time() - start_time)
                channel.busy.wait_for_state_change(0, timeout=remaining_timeout)
            return True

        ref_clock("internal", deep=True)
        logger.error(
            f"There was an error locking the device({self.serial}) "
            f"onto reference clock signal. Automatically switching to internal "
            f"reference clock. Please try again.",
        )
        return False
