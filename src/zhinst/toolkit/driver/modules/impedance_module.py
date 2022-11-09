"""Impedance Module."""

import logging
import typing as t
import time

from collections.abc import Sequence

from zhinst.core import ImpedanceModule as ZIImpedanceModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class CalibrationStatus(int, Sequence):
    """Wrapper around a Impedance module status.

    LabOne reports a status for the impedance module as integers.
    The integer needs to be interpreted in a binary format where each
    bit represents a stage within the compensation. If the bit is set it
    means that the step is completed.

    This class wraps around this by both deriving from an integer and a
    Sequence. Therefore one can use it like a int but also access the
    individual steps through items (e.g. module.step[0]).

    Args:
        value: Integer value of the status.

    .. versionadded:: 0.5.1
    """

    def __new__(cls, value: int):
        """New method of the CalibrationStatus.

        Args:
            value: Integer value of the status.
        """
        new_object = super(CalibrationStatus, cls).__new__(cls, value)
        new_object._value = value  # type: ignore[attr-defined]
        new_object._binary = new_object._to_binary()  # type: ignore[attr-defined]
        return new_object

    def __repr__(self):
        return ", ".join(
            [f"step {i}: {bool(value)}" for i, value in enumerate(self._binary)]
        )

    def _to_binary(self):
        binary = []
        num = self._value
        i = 0
        while num != 0:
            bit = int(num % 2)
            binary.insert(i, bit)
            i = i + 1
            num = int(num / 2)
        return binary

    def __getitem__(self, item):
        return self._binary[item] if len(self._binary) > item else 0

    def __len__(self):
        return len(self._binary)


class ImpedanceModule(BaseModule):
    """Implements a base Impedance Module for Lock-In instruments.

    The Impedance Module corresponds to the Cal sub-tab in the LabOne User
    Interface Impedance Analyzer tab. It allows the user to perform a
    compensation that will be applied to impedance measurements.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_programming_manual/impedance_module.html

    Args:
        impedance_module: Instance of the core Impedance Module.
        session: Session to the Data Server.

    .. versionadded:: 0.5.1
    """

    def __init__(self, impedance_module: ZIImpedanceModule, session: "Session"):
        super().__init__(impedance_module, session)
        self.root.update_nodes(
            {
                "/expectedstatus": {"GetParser": CalibrationStatus},
                "/status": {"GetParser": CalibrationStatus},
            },
            raise_for_invalid_node=False,
        )

    def wait_done(
        self,
        step: t.Optional[int] = None,
        *,
        timeout: float = 20.0,
        sleep_time: float = 0.5,
    ) -> None:
        """Waits until the specified compensation step is complete.

        Args:
            step: The compensation step to wait for completion.
            timeout: The maximum waiting time in seconds for the compensation
                to complete (default: 20).
            sleep_time: Time in seconds to wait between
                requesting the state. (default: 0.5)

        Raises:
            TimeoutError: The compensation is not completed before timeout.
        """
        start_time = time.time()
        while (
            start_time + timeout >= time.time()
            and self.calibrate()
            and not self.finished(step)
        ):
            logger.info(f"Progress: {(self.progress() * 100):.1f}%")
            time.sleep(sleep_time)
        if self.progress() < 1:
            raise TimeoutError("Impedance module timed out.")
        if not self.finished(step):
            if step is None:
                raise RuntimeError(
                    "Impedance module did not reach the status "
                    f"{CalibrationStatus(self.expectedstatus())} that "
                    "corresponds to a full compensation. "
                    f"(current status: {CalibrationStatus(self.status())})"
                )
            raise RuntimeError(
                f"Impedance module did not finish the requested step {step}. "
                f"(current status: {CalibrationStatus(self.status())})"
            )

    def finish(self) -> None:
        """Stop the module."""
        self._raw_module.finish()

    def finished(self, step: t.Optional[int] = None) -> bool:
        """Check if the calibration or a step of it is finished.

        Args:
            step: Calibration step. If not None this function checks if the
                specified step is finished. Otherwise it checks if the
                hole calibration is done.

        Returns:
            Flag if the calibration or a step is finished.
        """
        if step is None:
            return self.status() == self.expectedstatus()
        return self.status() & (1 << step)
