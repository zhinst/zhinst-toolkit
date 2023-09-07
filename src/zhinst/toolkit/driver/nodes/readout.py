"""zhinst-toolkit readout node adaptions."""
import logging
import typing as t

import numpy as np
import zhinst.utils.shfqa as utils
from zhinst.toolkit.exceptions import ToolkitError

from zhinst.toolkit.interface import AveragingMode
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import lazy_property, not_callable_in_transactions
from zhinst.toolkit.waveform import Waveforms
from zhinst.toolkit.driver.nodes.multistate import MultiState

logger = logging.getLogger(__name__)


class Readout(Node):
    """Readout node.

    Implements basic functionality of the readout, e.g allowing the user to
    write the integration weight.

    Args:
        root: Root of the nodetree
        tree: Tree (node path as tuple) of the current node
        serial: Serial of the device.
        index: Index of the corresponding awg channel
        max_qubits_per_channel: Max qubits per channel
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
        serial: str,
        index: int,
        max_qubits_per_channel: int,
    ):
        super().__init__(root, tree)
        self._daq_server = root.connection
        self._serial = serial
        self._index = index
        self._max_qubits_per_channel = max_qubits_per_channel

    def configure_result_logger(
        self,
        *,
        result_source: str,
        result_length: int,
        num_averages: int = 1,
        averaging_mode: AveragingMode = AveragingMode.CYCLIC,
    ) -> None:
        """Configures the result logger for readout mode.

        Args:
            result_source: String-based tag to select the result source in readout
                mode, e.g. "result_of_integration" or "result_of_discrimination".
            result_length: Number of results to be returned by the result logger
            num_averages: Number of averages, will be rounded to 2^n
            averaging_mode: Select the averaging order of the result, with
                0 = cyclic and 1 = sequential.
        """
        settings = utils.get_result_logger_for_readout_settings(
            self._serial,
            self._index,
            result_source=result_source,
            result_length=result_length,
            num_averages=num_averages,
            averaging_mode=int(averaging_mode),
        )
        self._send_set_list(settings)

    @not_callable_in_transactions
    def run(self) -> None:
        """Reset and enable the result logger."""
        utils.enable_result_logger(
            self._daq_server,
            self._serial,
            self._index,
            mode="readout",
        )

    def stop(self, *, timeout: float = 10, sleep_time: float = 0.05) -> None:
        """Stop the result logger.

        Args:
            timeout: The maximum waiting time in seconds for the Readout
                (default: 10).
            sleep_time: Sleep interval in seconds. (default = 0.05)

        Raises:
            TimeoutError: The result logger could not been stopped within the
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
        """Wait until the readout is finished.

        Args:
            timeout: The maximum waiting time in seconds for the Readout
                (default: 10).
            sleep_time: Sleep interval in seconds. (default = 0.05)

        Raises:
            TimeoutError: if the readout recording is not completed within the
                given time.
        """
        try:
            self.result.enable.wait_for_state_change(
                0, timeout=timeout, sleep_time=sleep_time
            )
        except TimeoutError as error:
            raise TimeoutError(
                f"{repr(self)}: The readout did not finish "
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
            Result logger data.
        """
        return utils.get_result_logger_data(
            self._daq_server, self._serial, self._index, mode="readout", timeout=timeout
        )

    @not_callable_in_transactions
    def write_integration_weights(
        self,
        weights: t.Union[Waveforms, dict],
        *,
        integration_delay: float = 0.0,
        clear_existing: bool = True,
    ) -> None:
        """Configures the weighted integration.

        Args:
            weights: Dictionary containing the complex weight vectors, where
                keys correspond to the indices of the integration units to be
                configured.
            integration_delay: Delay in seconds before starting the readout.
            clear_existing: Flag whether to clear the waveform memory before
                the present upload.
        """
        if (
            len(weights.keys()) > 0
            and max(weights.keys()) >= self._max_qubits_per_channel
        ):
            raise ToolkitError(
                f"The device only has {self._max_qubits_per_channel} qubits per channel"
                f", but {max(weights.keys())} were specified."
            )
        waveform_dict = {}
        if isinstance(weights, Waveforms):
            for slot in weights.keys():
                waveform_dict[slot] = weights.get_raw_vector(slot, complex_output=True)
        else:
            waveform_dict = weights

        utils.configure_weighted_integration(
            self._daq_server,
            self._serial,
            self._index,
            weights=waveform_dict,
            integration_delay=integration_delay,
            clear_existing=clear_existing,
        )

    def read_integration_weights(self, slots: t.List[int] = None) -> Waveforms:
        """Read integration weights from the waveform memory.

        Args:
            slots: List of weight slots to read from the device. If not specified
                all available weights will be downloaded.

        Returns:
            Mutable mapping of the downloaded weights.
        """
        nodes = []
        if slots is not None:
            for slot in slots:
                nodes.append(self.integration.weights[slot].wave.node_info.path)
        else:
            nodes.append(self.integration.weights["*"].wave.node_info.path)
        nodes_str = ",".join(nodes)
        weights_raw = self._daq_server.get(nodes_str, settingsonly=False, flat=True)
        weights = Waveforms()
        for slot, weight in enumerate(weights_raw.values()):
            weights[slot] = weight[0]["vector"]
        return weights

    @lazy_property
    def multistate(self) -> MultiState:
        """Multistate discrimination node tree branch."""
        return MultiState(
            self._root, self._tree + ("multistate",), self._serial, self._index
        )
