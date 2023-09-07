"""SHFQA Instrument Driver."""

import logging
import typing as t

import zhinst.utils.shfqa as utils

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.driver.nodes.readout import Readout
from zhinst.toolkit.driver.nodes.shfqa_scope import SHFScope
from zhinst.toolkit.driver.nodes.spectroscopy import Spectroscopy
from zhinst.toolkit.exceptions import ToolkitError
from zhinst.toolkit.interface import SHFQAChannelMode
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import (
    lazy_property,
    create_or_append_set_transaction,
    not_callable_in_transactions,
)
from zhinst.toolkit.nodetree.node import NodeList
from zhinst.toolkit.waveform import Waveforms

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session


class Generator(AWG):
    """Generator node.

    Implements basic functionality of the generator allowing the user to write
    and upload their *'.seqC'* code.

    In contrast to other AWG Sequencers, e.g. from the HDAWG, SHFSG
    it does not provide writing access to the Waveform Memories
    and hence does not come with predefined waveforms such as `gauss`
    or `ones`. Therefore, all waveforms need to be defined in Python
    and uploaded to the device using `upload_waveforms` method.

    Args:
        root: Root of the nodetree
        tree: Tree (node path as tuple) of the current node
        daq_server: Instance of the ziDAQServer
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
        device_type: str,
        device_options: str,
    ):
        super().__init__(root, tree, serial, index, device_type, device_options)
        self._max_qubits_per_channel = max_qubits_per_channel

    def write_to_waveform_memory(
        self, pulses: t.Union[Waveforms, dict], *, clear_existing: bool = True
    ) -> None:
        """Writes pulses to the waveform memory.

        Args:
            pulses: Waveforms that should be uploaded.
            clear_existing: Flag whether to clear the waveform memory before the
                present upload. (default = True)
        """
        if (
            len(pulses.keys()) > 0
            and max(pulses.keys()) >= self._max_qubits_per_channel
        ):
            raise ToolkitError(
                f"The device only has {self._max_qubits_per_channel} qubits per channel"
                f", but {max(pulses.keys())} were specified."
            )
        with create_or_append_set_transaction(self._root):
            if clear_existing:
                self.clearwave(1)
            if isinstance(pulses, Waveforms):
                for slot in pulses.keys():
                    self.waveforms[slot].wave(
                        pulses.get_raw_vector(slot, complex_output=True)
                    )
            else:
                for slot, waveform in pulses.items():
                    self.waveforms[slot].wave(waveform)

    def read_from_waveform_memory(self, slots: t.List[int] = None) -> Waveforms:
        """Read pulses from the waveform memory.

        Args:
            slots: List of waveform indexes to read from the device. If not
                specified all assigned waveforms will be downloaded.

        Returns:
            Mutable mapping of the downloaded waveforms.
        """
        nodes = []
        if slots is not None:
            for slot in slots:
                nodes.append(self.waveforms[slot].wave.node_info.path)
        else:
            nodes.append(self.waveforms["*"].wave.node_info.path)
        nodes_str = ",".join(nodes)
        waveforms_raw = self._daq_server.get(nodes_str, settingsonly=False, flat=True)
        waveforms = Waveforms()
        for slot, waveform in enumerate(waveforms_raw.values()):
            waveforms[slot] = waveform[0]["vector"]
        return waveforms

    def configure_sequencer_triggering(
        self, *, aux_trigger: str, play_pulse_delay: float = 0.0
    ) -> None:
        """Configure the sequencer triggering.

        Args:
            aux_trigger: Alias for the trigger source used in the sequencer.
                For the list of available values, use `available_aux_trigger_inputs`
            play_pulse_delay: Delay in seconds before the start of waveform playback.
        """
        # Only Digital Trigger 1
        settings = utils.get_sequencer_triggering_settings(
            self._serial,
            self._index,
            aux_trigger=aux_trigger,
            play_pulse_delay=play_pulse_delay,
        )
        self._send_set_list(settings)

    @property
    def available_aux_trigger_inputs(self) -> t.List[str]:
        """List of available aux trigger sources for the generator."""
        return [
            option.enum
            for option in self.auxtriggers[0].channel.node_info.options.values()
        ]


class QAChannel(Node):
    """Quantum Analyzer Channel for the SHFQA.

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
        settings = utils.get_channel_settings(
            self._serial,
            self._index,
            input_range=input_range,
            output_range=output_range,
            center_frequency=center_frequency,
            mode=mode.value,
        )
        self._send_set_list(settings)

    @lazy_property
    def generator(self) -> Generator:
        """Generator."""
        return Generator(
            self._root,
            self._tree + ("generator",),
            self._device.serial,
            self._index,
            self._device.max_qubits_per_channel,
            self._device.device_type,
            self._device.device_options,
        )

    @lazy_property
    def readout(self) -> Readout:
        """Readout."""
        return Readout(
            self._root,
            self._tree + ("readout",),
            self._device.serial,
            self._index,
            self._device.max_qubits_per_channel,
        )

    @lazy_property
    def spectroscopy(self) -> Spectroscopy:
        """Spectroscopy."""
        return Spectroscopy(
            self._root,
            self._tree + ("spectroscopy",),
            self._device.serial,
            self._index,
        )


class SHFQA(BaseInstrument):
    """High-level driver for the Zurich Instruments SHFQA."""

    @not_callable_in_transactions
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
        utils.start_continuous_sw_trigger(
            self._session.daq_server,
            self.serial,
            num_triggers=num_triggers,
            wait_time=wait_time,
        )

    @lazy_property
    def max_qubits_per_channel(self) -> int:
        """Maximum number of supported qubits per channel."""
        return utils.max_qubits_per_channel(self._session.daq_server, self.serial)

    @lazy_property
    def qachannels(self) -> t.Sequence[QAChannel]:
        """A Sequence of QAChannels."""
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
        """A Sequence of SHFScopes."""
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
