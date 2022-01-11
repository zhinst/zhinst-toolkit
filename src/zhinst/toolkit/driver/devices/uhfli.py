"""UHFLI Instrument Driver."""

import logging
import typing as t

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.nodetree.helper import lazy_property
from zhinst.toolkit.nodetree.node import NodeList

logger = logging.getLogger(__name__)


class UHFLI(BaseInstrument):
    """High-level driver for the Zurich Instruments UHFLI."""

    @lazy_property
    def awgs(self) -> t.Sequence[AWG]:
        """A Sequence of AWG Cores"""
        if "AWG" not in self.features.options():
            logger.error("The AWG option is not installed.")
        return NodeList(
            [
                AWG(
                    self.root,
                    self._tree + ("awgs", str(i)),
                    self._session.modules.awg,
                    self._session.daq_server,
                    self.serial,
                    i,
                    self.device_type,
                )
                for i in range(len(self["awgs"]))
            ],
            self._root,
            self._tree + ("awgs",),
        )
