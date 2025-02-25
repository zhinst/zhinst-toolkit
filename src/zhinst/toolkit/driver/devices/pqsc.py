"""PQSC Instrument Driver."""

from __future__ import annotations

from typing import Optional

from zhinst.toolkit.driver.devices.quantum_system_hub import QuantumSystemHub


class PQSC(QuantumSystemHub):
    """High-level driver for the Zurich Instruments PQSC."""

    def arm(
        self,
        *,
        deep=True,
        repetitions: Optional[int] = None,
        holdoff: Optional[float] = None,
    ) -> None:
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
