"""DAQ Module."""

import logging
import typing as t
from collections import namedtuple

import numpy as np
from zhinst.ziPython import DataAcquisitionModule as ZIDAQModule

from zhinst.toolkit.driver.modules.base_module import BaseModule
from zhinst.toolkit.nodetree import Node

if t.TYPE_CHECKING:
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)
DAQResult = namedtuple("DAQResult", ["header", "value", "time", "frequency", "shape"])


class DAQModule(BaseModule):
    """Data Acquisition Module.

    The Data Acquisition Module corresponds to the Data Acquisition tab of the
    LabOne User Interface. It enables the user to record and align time and
    frequency domain data from multiple instrument signal sources at a defined
    data rate. The data may be recorded either continuously or in bursts based
    upon trigger criteria analogous to the functionality provided by laboratory
    oscilloscopes.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_programming_manual/data_acquisition_module.html

    Args:
        daq_module: Instance of the ziPython DAQ module.
        session: Session to the Data Server.
    """

    def __init__(self, daq_module: ZIDAQModule, session: "Session"):
        super().__init__(daq_module, session)
        self.root.update_nodes(
            {
                "/triggernode": {
                    "GetParser": self._get_node,
                    "SetParser": self._set_node,
                }
            }
        )

    def _get_node(self, node: str) -> t.Union[Node, str]:
        """Convert a raw node string into a toolkit node.

        Overwrites the base_module._get_node function and adds the support for
        the signal subscription options.

        Args:
            node (str): Raw node string

        Returns:
            Node: Toolkit node. (if the node can not be converted the raw node
                string is returned)
        """
        try:
            return self._session.raw_path_to_node(node.replace(".", "/"), module=self)
        except (KeyError, RuntimeError):
            logger.error(
                f"Could not resolve {node} into a node of the sweeper module or "
                " a connected device."
            )
            return node

    @staticmethod
    def _set_node(signal: t.Union[Node, str]) -> str:
        """Convert a toolkit node into a raw node string.

        Support the signal subscription options.

        Args:
            signal: A node

        Returns:
            str: A raw string representation of Node
        """
        try:
            node = signal.node_info.path
        except AttributeError:
            node = signal
        sample_pos = node.find("sample")
        if sample_pos != -1:
            node = node[:sample_pos] + node[sample_pos:].replace("/", ".")
        return node

    def execute(self) -> None:
        """Start the data acquisition.
    
        After that command any trigger will start the measurement.

        Subscription or unsubscription is not possible until the
        acquisition is finished.
        """
        self._raw_module.execute()

    def subscribe(self, signal: Node) -> None:
        """Subscribe to a node.

        The node can either be a node of this module or of a connected device.

        Support the signal subscription options of the daq module.
        For more information on the signal options see:
        https://docs.zhinst.com/labone_programming_manual/data_acquisition_module.html

        Args:
            signal: A node that should be subscribed to.
        """
        self._raw_module.subscribe(self._set_node(signal))

    def unsubscribe(self, signal: Node) -> None:
        """Unsubscribe from a node.

        The node can either be a node of this module or of a connected device.

        Args:
            signal: A node that should be unsubscribed from.
        """
        self._raw_module.unsubscribe(self._set_node(signal))

    def read(
        self, *, raw: bool = False, clk_rate: float = 60e6
    ) -> t.Dict[t.Union[Node, str], t.Union[t.List[DAQResult], t.Any]]:
        """Read the acquired data from the module.

        The data is split into bursts.

        Args:
            raw: Flag if the acquired data from the subscribed device
                device nodes should be converted into the DAQResult format
                (raw = False) or not. (default = False)
            clk_rate: Clockrate [Hz] for converting the timestamps. Only
                applies if the raw flag is reset.

        Returns:
            Result of the burst grouped by the signals.
        """
        raw_result = self._raw_module.read(flat=True)
        results = {}
        for node, node_results_raw in raw_result.items():
            if not raw and isinstance(node_results_raw[0], dict):
                node_results = []
                for result_dict in node_results_raw:
                    if "fft" in node:
                        bin_count = len(result_dict.get("value")[0])
                        bin_resolution = result_dict.get("header")["gridcoldelta"]
                        frequency = np.arange(bin_count)
                        bandwidth = bin_resolution * len(frequency)
                        frequency = frequency * bin_resolution
                        if "xiy" in node:
                            frequency = (
                                frequency - bandwidth / 2.0 + bin_resolution / 2.0
                            )
                        node_results.append(
                            DAQResult(
                                result_dict.get("header", {}),
                                result_dict.get("value"),
                                None,
                                frequency,
                                result_dict.get("value").shape,
                            )
                        )
                    else:
                        timestamp = result_dict.get("timestamp")
                        node_results.append(
                            DAQResult(
                                result_dict.get("header", {}),
                                result_dict.get("value"),
                                (timestamp[0] - timestamp[0][0]) / clk_rate,
                                None,
                                result_dict.get("value").shape,
                            )
                        )
                node_results_raw = node_results
            results[self._get_node(node)] = node_results_raw
        return results
