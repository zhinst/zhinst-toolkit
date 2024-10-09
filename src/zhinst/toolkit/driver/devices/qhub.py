"""QHub Instrument Driver."""

from zhinst.toolkit.driver.devices.quantum_system_hub import QuantumSystemHub


class QHub(QuantumSystemHub):
    """High-level driver for the Zurich Instruments QHub."""

    def arm(self, *, deep=True, repetitions: int = None, holdoff: float = None) -> None:
        """Prepare QHub for triggering the instruments.

        This method configures the execution engine of QHub.
        Optionally, the *number of triggers*
        and *hold-off time* can be set when specified as keyword
        arguments. If they are not specified, they are not changed.

        Note that the QHub is disabled at the end of the hold-off time
        after sending out the last trigger.

        Args:
            deep: A flag that specifies if a synchronization
                should be performed between the device and the data
                server after stopping QHub (default: True).
            repetitions: If specified, the number of triggers sent
                over ZSync ports will be set (default: None).
            holdoff: If specified, the time between repeated
                triggers sent over ZSync ports will be set. It has a
                minimum value and a granularity of 100 ns
                (default: None).

        """
        # Stop QHub if it is already running
        self.stop(deep=deep)
        if repetitions is not None:
            self.execution.repetitions(repetitions)
        if holdoff is not None:
            self.execution.holdoff(holdoff)
