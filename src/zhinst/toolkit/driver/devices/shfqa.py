"""SHFQA Instrument Driver."""

import logging
import typing as t
import warnings

import zhinst.deviceutils.shfqa as deviceutils

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.generator import Generator
from zhinst.toolkit.driver.nodes.readout import Readout
from zhinst.toolkit.driver.nodes.shfqa_scope import SHFScope
from zhinst.toolkit.driver.nodes.spectroscopy import Spectroscopy
from zhinst.toolkit.interface import SHFQAChannelMode
from zhinst.toolkit.nodetree import Node
from zhinst.toolkit.nodetree.helper import lazy_property
from zhinst.toolkit.nodetree.node import NodeList

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from zhinst.toolkit.session import Session


class QAChannel(Node):
    """Quantum Analyser Channel for the SHFQA.

    :class:`QAChannel` implements basic functionality to configure QAChannel
    settings of the :class:`SHFQA` instrument.
    Besides the :class:`Generator`, :class:`Readout` and :class:`Sweeper`
    modules it also provides an easy access to commonly used `QAChannel` parameters.

    Args:
        device: SHFQA device object.
        session: Underlying session.
        tree: Node tree (node path as tuple) of the corresponding node.
    """

    def __init__(
        self,
        device: "SHFQA",
        session: "Session",
        tree: t.Tuple[str, ...],
    ):
        super().__init__(device.root, tree)
        self._index = int(tree[-1])
        self._device = device
        self._serial = device.serial
        self._session = session

    def configure_channel(
        self,
        *,
        input_range: int,
        output_range: int,
        center_frequency: float,
        mode: SHFQAChannelMode,
    ) -> None:
        """Configures the RF input and output of a specified channel.

        Args:
            input_range: Maximal range of the signal input power in dBm
            output_range: Maximal range of the signal output power in dBm
            center_frequency: Center frequency of the analysis band [Hz]
            mode: Select between spectroscopy and readout mode.
        """
        deviceutils.configure_channel(
            self._session.daq_server,
            self._serial,
            self._index,
            input_range=input_range,
            output_range=output_range,
            center_frequency=center_frequency,
            mode=mode.value,
        )

    @lazy_property
    def generator(self) -> Generator:
        """Generator"""
        return Generator(
            self._root,
            self._tree + ("generator",),
            self._session.daq_server,
            self._device.serial,
            self._index,
            self._device.max_qubits_per_channel,
        )

    @lazy_property
    def readout(self) -> Readout:
        """Readout"""
        return Readout(
            self._root,
            self._tree + ("readout",),
            self._session.daq_server,
            self._device.serial,
            self._index,
            self._device.max_qubits_per_channel,
        )

    @lazy_property
    def spectroscopy(self) -> Spectroscopy:
        """Spectroscopy"""
        return Spectroscopy(
            self._root,
            self._tree + ("spectroscopy",),
            self._session.daq_server,
            self._device.serial,
            self._index,
        )


class SHFQA(BaseInstrument):
    """High-level driver for the Zurich Instruments SHFQA."""

    def factory_reset(self, *, deep: bool = True) -> None:
        """Load the factory default settings.

        Args:
            deep: A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).
        """
        warnings.warn("Factory preset is not yet supported for SHFQA.", RuntimeWarning)
        logger.warning("Factory preset is not yet supported in SHFQA.")

    def start_continuous_sw_trigger(
        self, *, num_triggers: int, wait_time: float
    ) -> None:
        """Issues a specified number of software triggers.

        Issues a specified number of software triggers with a certain wait time
        in between. The function guarantees reception and proper processing of
        all triggers by the device, but the time between triggers is
        non-deterministic by nature of software triggering. Only use this
        function for prototyping and/or cases without strong timing requirements.

        Args:
            num_triggers: Number of triggers to be issued
            wait_time: Time between triggers in seconds
        """

        deviceutils.start_continuous_sw_trigger(
            self._session.daq_server, self.serial, num_triggers=num_triggers, wait_time=wait_time
        )

    @lazy_property
    def max_qubits_per_channel(self) -> int:
        """Maximum number of supported qubits per channel."""
        return deviceutils.max_qubits_per_channel(self._session.daq_server, self.serial)

    @lazy_property
    def qachannels(self) -> t.Sequence[QAChannel]:
        """A Sequence of QAChannels"""
        return NodeList(
            [
                QAChannel(self, self._session, self._tree + ("qachannels", str(i)))
                for i in range(len(self["qachannels"]))
            ],
            self._root,
            self._tree + ("qachannels",),
        )

    @lazy_property
    def scopes(self) -> t.Sequence[SHFScope]:
        """A Sequence of SHFScopes"""
        return NodeList(
            [
                SHFScope(
                    self._root,
                    self._tree + ("scopes", str(i)),
                    self._session.daq_server,
                    self.serial,
                )
                for i in range(len(self["scopes"]))
            ],
            self._root,
            self._tree + ("scopes",),
        )
