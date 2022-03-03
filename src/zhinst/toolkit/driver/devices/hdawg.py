"""HDAWG Instrument Driver."""
import typing as t

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.nodetree.helper import (
    create_or_append_set_transaction,
    lazy_property,
)
from zhinst.toolkit.nodetree.node import NodeList


class HDAWG(BaseInstrument):
    """High-level driver for the Zurich Instruments HDAWG."""

    def enable_qccs_mode(self) -> None:
        """Configure the instrument to work with PQSC

        This method sets the reference clock source to
        connect the instrument to the PQSC.

        Info:
            Use ``factory_reset`` to reset the changes if necessary
        """
        with create_or_append_set_transaction(self._root):
            # Set ZSync clock to be used as reference
            self.system.clocks.referenceclock.source("zsync")
            # Configure DIO
            # Set interface standard to use on the 32-bit DIO to LVCMOS
            self.dios[0].interface(0)
            # Set DIO output values to ZSync input values.
            # Forward the ZSync input values to the AWG sequencer.
            # Forward the DIO input values to the ZSync output.
            self.dios[0].mode("qccs")
            # Drive the two most significant bytes of the DIO port
            self.dios[0].drive(0b1100)
            # Disable DIO triggering on the AWGs,
            # since it's not needed for ZSync messages
            self.awgs['*'].dio.strobe.slope('off')
            self.awgs['*'].dio.valid.polarity('none')

    @lazy_property
    def awgs(self) -> t.Sequence[AWG]:
        """A Sequence of AWG Cores"""
        return NodeList(
            [
                AWG(
                    self.root,
                    self._tree + ("awgs", str(i)),
                    self._session,
                    self.serial,
                    i,
                    "hdawg",
                )
                for i in range(len(self["awgs"]))
            ],
            self._root,
            self._tree + ("awgs",),
        )
