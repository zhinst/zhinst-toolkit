"""DAQ Module."""

import logging
import typing as t
from collections import namedtuple

import numpy as np
from zhinst.core import DataAcquisitionModule as ZIDAQModule

from zhinst.toolkit.driver.modules.base_module import BaseModule
from zhinst.toolkit.nodetree.helper import NodeDict

if t.TYPE_CHECKING:  # pragma: no cover
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
        daq_module: Instance of the core DAQ module.
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
            },
            raise_for_invalid_node=False,
        )

    @staticmethod
    def _process_burst(
        node: str, burst: t.Dict[str, t.Any], clk_rate: float
    ) -> DAQResult:
        """Process a single burst into a formatted DAQResult object.

        Args:
            node: Name of the node of the burst.
            burst: raw burst data.
            clk_rate: Clock rate [Hz] for converting the timestamps. Only
                applies if the raw flag is reset.

        Returns:
                Processed and formatted burst data.
        """
        if "fft" in node:
            bin_count = len(burst["value"][0])
            bin_resolution = burst["header"]["gridcoldelta"]
            frequency = np.arange(bin_count)
            bandwidth = bin_resolution * len(frequency)
            frequency = frequency * bin_resolution
            if "xiy" in node:
                frequency = frequency - bandwidth / 2.0 + bin_resolution / 2.0
            return DAQResult(
                burst.get("header", {}),
                burst["value"],
                None,
                frequency,
                burst["value"].shape,
            )
        timestamp = burst["timestamp"]
        return DAQResult(
            burst.get("header", {}),
            burst["value"],
            (timestamp[0] - timestamp[0][0]) / clk_rate,
            None,
            burst["value"].shape,
        )

    @staticmethod
    def _process_node_data(
        node: str, data: t.List[t.Dict[str, t.Any]], clk_rate: float
    ) -> t.List[t.Union[t.Dict[str, t.Any], DAQResult]]:
        """Process the data of a node.

        Only subscribed sample nodes are processed. Other nodes (module native nodes)
        are returned in the original format.

        Args:
            node: Name of the node of the burst.
            data: raw data for the node.
            clk_rate: Clock rate [Hz] for converting the timestamps. Only
                applies if the raw flag is reset.

        Returns:
                Processed and formatted node data.
        """
        if isinstance(data[0], dict):
            return [DAQModule._process_burst(node, burst, clk_rate) for burst in data]
        return data

    def finish(self) -> None:
        """Stop the module.

        .. versionadded:: 0.5.0
        """
        self._raw_module.finish()

    def finished(self) -> bool:
        """Check if the acquisition has finished.

        Returns:
            Flag if the acquisition has finished.

        .. versionadded:: 0.5.0
        """
        return self._raw_module.finished()

    def trigger(self) -> None:
        """Execute a manual trigger.

        .. versionadded:: 0.5.0
        """
        self._raw_module.trigger()

    def read(self, *, raw: bool = False, clk_rate: float = 60e6) -> NodeDict:
        """Read the acquired data from the module.

        The data is split into bursts.

        Args:
            raw: Flag if the acquired data from the subscribed device
                device nodes should be converted into the DAQResult format
                (raw = False) or not. (default = False)
            clk_rate: Clock rate [Hz] for converting the timestamps. Only
                applies if the raw flag is reset.

        Returns:
            Result of the burst grouped by the signals.
        """
        raw_result = self._raw_module.read(flat=True)
        if raw:
            return NodeDict(raw_result)
        return NodeDict(
            {
                node: self._process_node_data(node, data, clk_rate)
                for node, data in raw_result.items()
            }
        )
