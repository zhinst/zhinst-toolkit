"""HDAWG Instrument Driver."""
import typing as t

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.nodetree.helper import (
    create_or_append_set_transaction,
    lazy_property,
)
from zhinst.toolkit.nodetree.node import NodeList
from zhinst.toolkit.exceptions import ToolkitError


class HDAWG(BaseInstrument):
    """High-level driver for the Zurich Instruments HDAWG."""

    def enable_qccs_mode(self, gen: int = 1) -> None:
        """Configure the instrument to work with PQSC.

        This method sets the reference clock source to
        connect the instrument to the PQSC.

        Args:
            gen: The QCCS generation that is being configured.
                 Use 1 for a gen1 system, when only HDAWG and UHFQA are used.
                 In this case, the sample rate is set to 2.4 GSa/s and the DIO
                 interface is configured for connection with the UHFQA.
                 Use 2 for a gen2 system, when only HDAWG and SHFs are used.
                 In this case, the sample rate is set to 2.0 GSa/s.
                 (default: 1)

            .. versionchanged:: 0.6.2: Added gen parameter.

        Raises:
            ToolkitError: If the gen argument is not correct.

        Info:
            Use ``factory_reset`` to reset the changes if necessary
        """
        with create_or_append_set_transaction(self._root):
            # Enable QCCS mode, so the instrument is able
            # to operate with ZSync
            self.dios[0].mode("qccs")

            # Gen1 specific elements
            if gen == 1:
                # Set the sample clock to 2.4 GSa/s
                self.system.clocks.sampleclock.freq(2.4e9)
                # Configure DIO
                # Set interface standard to use on the 32-bit DIO to LVCMOS
                self.dios[0].interface(0)
                # Drive the two most significant bytes of the DIO port
                # so the UHFQA receives triggers from PQSC
                self.dios[0].drive(0b1100)

            # Gen2 specific elements
            elif gen == 2:
                # Set the sample clock to 2.0 GSa/s
                self.system.clocks.sampleclock.freq(2.0e9)
                # Turn off DIO
                self.dios[0].drive(0b0000)

            else:
                raise ToolkitError("Only gen1 or gen2 are supported!")

            # Set ZSync clock to be used as reference
            self.system.clocks.referenceclock.source("zsync")

            # Disable DIO triggering on the AWGs,
            # since it's not needed for ZSync messages
            self.awgs["*"].dio.strobe.slope("off")
            self.awgs["*"].dio.valid.polarity("none")

    @lazy_property
    def awgs(self) -> t.Sequence[AWG]:
        """A Sequence of AWG Cores."""
        return NodeList(
            [
                AWG(
                    self.root,
                    self._tree + ("awgs", str(i)),
                    self.serial,
                    i,
                    self.device_type,
                    self.device_options,
                )
                for i in range(len(self["awgs"]))
            ],
            self._root,
            self._tree + ("awgs",),
        )
