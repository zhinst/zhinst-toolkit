"""zhinst-toolkit spectroscopy node adaptions."""
import logging

import numpy as np
import zhinst.utils.shfqa as utils

from zhinst.toolkit.interface import AveragingMode
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import not_callable_in_transactions

logger = logging.getLogger(__name__)


class Spectroscopy(Node):
    """Spectroscopy node.

    Implements basic functionality of the spectroscopy, e.g allowing the user to
    read the result logger data.

    Args:
        root: Root of the nodetree
        tree: Tree (node path as tuple) of the current node
        serial: Serial of the device.
        index: Index of the corresponding awg channel
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
        serial: str,
        index: int,
    ):
        super().__init__(root, tree)
        self._daq_server = root.connection
        self._serial = serial
        self._index = index

    def configure_result_logger(
        self,
        *,
        result_length: int,
        num_averages: int = 1,
        averaging_mode: AveragingMode = AveragingMode.CYCLIC,
    ) -> None:
        """Configures the result logger for spectroscopy mode.

        Args:
            result_length: Number of results to be returned by the result logger
            num_averages: Number of averages, will be rounded to 2^n.
            averaging_mode: Averaging order of the result.
        """
        settings = utils.get_result_logger_for_spectroscopy_settings(
            self._serial,
            self._index,
            result_length=result_length,
            num_averages=num_averages,
            averaging_mode=int(averaging_mode),
        )
        self._send_set_list(settings)

    @not_callable_in_transactions
    def run(self) -> None:
        """Resets and enables the spectroscopy result logger."""
        utils.enable_result_logger(
            self._daq_server,
            self._serial,
            self._index,
            mode="spectroscopy",
        )

    def stop(self, *, timeout: float = 10, sleep_time: float = 0.05) -> None:
        """Stop the result logger.

        Args:
            timeout: The maximum waiting time in seconds for the
                Spectroscopy (default: 10).
            sleep_time: Time in seconds to wait between
                requesting Spectroscopy state
        Raises:
            TimeoutError: If the result logger could not been stopped within the
                given time.

        """
        self.result.enable(False)
        try:
            self.result.enable.wait_for_state_change(
                0, timeout=timeout, sleep_time=sleep_time
            )
        except TimeoutError as error:
            raise TimeoutError(
                f"{repr(self)}: The result logger could not been stopped "
                f"within the specified timeout ({timeout}s)."
            ) from error

    def wait_done(self, *, timeout: float = 10, sleep_time: float = 0.05) -> None:
        """Wait until spectroscopy is finished.

        Args:
            timeout (float): The maximum waiting time in seconds for the
                Spectroscopy (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting Spectroscopy state

        Raises:
            TimeoutError: if the spectroscopy recording is not completed within the
                given time.

        """
        try:
            self.result.enable.wait_for_state_change(
                0, timeout=timeout, sleep_time=sleep_time
            )
        except TimeoutError as error:
            raise TimeoutError(
                f"{repr(self)}: The spectroscopy did not finish "
                f"within the specified timeout ({timeout}s)."
            ) from error

    @not_callable_in_transactions
    def read(
        self,
        *,
        timeout: float = 10,
    ) -> np.array:
        """Waits until the logger finished recording and returns the measured data.

        Args:
            timeout: Maximum time to wait for data in seconds (default = 10s)

        Returns:
            An array containing the result logger data.

        """
        return utils.get_result_logger_data(
            self._daq_server,
            self._serial,
            self._index,
            mode="spectroscopy",
            timeout=timeout,
        )
