"""PID Advisor Module."""
import logging
import typing as t
import time
from enum import IntFlag

from zhinst.core import PidAdvisorModule as ZIPidAdvisorModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class PIDMode(IntFlag):
    """PID Advisor mode.

    P_Gain:         Optimize/Tune P gain.
    I_Gain:         Optimize/Tune I gain.
    D_Gain:         Optimize/Tune D gain.
    D_Filter_Limit: Optimize/Tune D filter limit.

    .. versionadded:: 0.5.1
    """

    NONE = 0
    P_Gain = 1
    I_Gain = 2
    D_Gain = 4
    D_Filter_Limit = 8


class PIDAdvisorModule(BaseModule):
    """PID Advisor Module.

    The PID Advisor Module provides the functionality available in the Advisor,
    Tuner and Display sub-tabs of the LabOne User Interface’s PID / PLL tab.
    The PID Advisor is a mathematical model of the instrument’s PID and can be
    used to calculate PID controller parameters for optimal feedback loop
    performance. The controller gains calculated by the module can be easily
    transferred to the device via the API and the results of the Advisor’s
    modeling are available as Bode and step response plot data.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_programming_manual/pid_advisor_module.html

    Args:
        pid_advisor_module: Instance of the core PID advisor module.
        session: Session to the Data Server.

    .. versionadded:: 0.5.1
    """

    def __init__(self, pid_advisor_module: ZIPidAdvisorModule, session: "Session"):
        super().__init__(pid_advisor_module, session)
        self.root.update_nodes(
            {
                "/pid/mode": {
                    "GetParser": PIDMode,
                },
                "/tuner/mode": {
                    "GetParser": PIDMode,
                },
            },
            raise_for_invalid_node=False,
        )

    def wait_done(self, *, timeout: float = 20.0, sleep_time: float = 2) -> None:
        """Waits until the pid advisor is finished.

        Args:
            timeout (float): The maximum waiting time in seconds for the
                measurement (default: 20).
            sleep_time (int): Time in seconds to wait between
                requesting sweeper state. (default: 0.5)

        Raises:
            TimeoutError: The measurement is not completed before
                timeout.
        """
        start_time = time.time()
        while start_time + timeout >= time.time() and (
            self.calculate()
            or (not self._raw_module.finished() and self.progress() != 1)
        ):
            # When the advisor is started it takes some time to reset the
            # progress (and finished) node. This causes weird behavior when
            # restarted. This if statement just ignores the progress until it
            # is smaller than 100%
            if self.progress() < 1:
                logger.info(f"Progress: {(self.progress() * 100):.1f}%")
            else:
                logger.info("Progress: 0.0%")
            time.sleep(sleep_time)
        if self.calculate() or (
            not self._raw_module.finished() and self.progress() != 1
        ):
            raise TimeoutError(f"{self._raw_module.__class__.__name__} timed out.")
        logger.info(f"Progress: {(self.progress() * 100):.1f}%")
