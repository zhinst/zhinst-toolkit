"""zhinst-toolkit multistate node adaptions."""
import typing as t

import numpy as np
import zhinst.utils.shfqa.multistate as utils

from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.node import NodeList
from zhinst.toolkit.nodetree.helper import (
    lazy_property,
    create_or_append_set_transaction,
)


class Qudit(Node):
    """Single Qudit node.

    Implements basic functionality of a single qudit node, e.g applying the
    basic configuration.

    Args:
        root: Root of the nodetree.
        tree: Tree (node path as tuple) of the current node.
        serial: Serial of the device.
        readout_channel: Index of the readout channel this qudit belongs to.
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
        serial: str,
        readout_channel: int,
    ):
        super().__init__(root, tree)
        self._daq_server = root.connection
        self._serial = serial
        self._readout_channel = readout_channel

    def configure(
        self,
        qudit_settings: utils.QuditSettings,
        enable: bool = True,
    ) -> None:
        """Compiles a list of transactions to apply the qudit settings to the device.

        Args:
            qudit_settings: The qudit settings to be configured.
            enable: Whether to enable the qudit. (default: True)

        """
        settings = utils.get_settings_transaction(
            self._serial,
            self._readout_channel,
            int(self._tree[-1]),
            qudit_settings,
            enable=enable,
        )
        with create_or_append_set_transaction(self._root):
            for node, value in settings:
                self._root.transaction.add(node, value)


class MultiState(Node):
    """MultiState node.

    Implements basic functionality of the MultiState node.

    Args:
        root: Root of the nodetree.
        tree: Tree (node path as tuple) of the current node.
        serial: Serial of the device.
        index: Index of the corresponding readout channel.
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

    def get_qudits_results(self) -> t.Dict[int, np.ndarray]:
        """Downloads the qudit results from the device and group them by qudit.

        This function accesses the multistate nodes to determine which
        integrators were used for which qudit to able to group the results by
        qudit.

        Returns:
            A dictionary with the qudit index keys and result vector values.
        """
        return utils.get_qudits_results(
            self._daq_server,
            self._serial,
            self._index,
        )

    @lazy_property
    def qudits(self) -> t.Sequence[Qudit]:
        """A Sequence of Qudits."""
        return NodeList(
            [
                Qudit(
                    self._root,
                    self._tree + ("qudits", str(i)),
                    self._serial,
                    self._index,
                )
                for i in range(len(self["qudits"]))
            ],
            self._root,
            self._tree + ("qudits",),
        )
