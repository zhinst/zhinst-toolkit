"""UHFLI Instrument Driver."""

from __future__ import annotations

import logging
import typing as t
from functools import cached_property

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.nodetree.node import Node, NodeList

logger = logging.getLogger(__name__)


class UHFLI(BaseInstrument):
    """High-level driver for the Zurich Instruments UHFLI."""

    @cached_property
    def awgs(self) -> t.Union[t.Sequence[AWG], Node]:
        """A Sequence of AWG Cores.

        Device options requirement(s): AWG

        Returns:
            A list of AWG Cores or a single AWG Core node.
        """
        if "AWG" not in self.features.options():
            logger.error("Missing option: AWG")
            return Node(
                self._root,
                (*self._tree, "awgs"),
            )
        return NodeList(
            [
                AWG(
                    self.root,
                    (*self._tree, "awgs", str(i)),
                    self.serial,
                    i,
                    self.device_type,
                    self.device_options,
                )
                for i in range(len(self["awgs"]))
            ],
            self._root,
            (*self._tree, "awgs"),
        )
