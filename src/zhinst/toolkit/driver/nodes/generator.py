"""zhinst-toolkit generator node adaptions."""
import logging
import typing as t

import zhinst.deviceutils.shfqa as deviceutils
from zhinst.ziPython import ziDAQServer

from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.waveform import Waveforms

logger = logging.getLogger(__name__)


class Generator(Node):
    """Generator node

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
        index: Index of the coresponding awg channel
        max_qubits_per_channel: Max qubits per channel
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
        daq_server: ziDAQServer,
        serial: str,
        index: int,
        max_qubits_per_channel: int,
    ):
        super().__init__(root, tree)
        self._daq_server = daq_server
        self._serial = serial
        self._index = index
        self._max_qubits_per_channel = max_qubits_per_channel

    def enable_sequencer(self, *, single: bool) -> None:
        """Starts the sequencer.

        Args:
            single: Flag if the sequencer should be disabled after finishing
            execution.
        """
        deviceutils.enable_sequencer(
            self._daq_server,
            self._serial,
            self._index,
            single=int(single),
        )

    def wait_done(self, *, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the generator execution is finished.

        Args:
            timeout: The maximum waiting time in seconds for the generator
                (default: 10).
            sleep_time: Time in seconds to wait between requesting generator
                state.

        Raises:
            RuntimeError: If continuous mode is enabled
            TimeoutError: If the sequencer program did not finish within the
                specified timeout time.
        """
        if not self.single():
            raise RuntimeError(
                f"{repr(self)}: The generator is running in continuous mode, "
                "it will never be finished."
            )
        try:
            self.enable.wait_for_state_change(0, timeout=timeout, sleep_time=sleep_time)
        except TimeoutError as error:
            raise TimeoutError(
                f"{repr(self)}: The execution of the sequencer program did not finish "
                f"within the specified timeout ({timeout}s)."
            ) from error

    def load_sequencer_program(
        self, sequencer_program: str, *, timeout: float = 10
    ) -> None:
        """Compiles and loads a sequencer program.

        Args:
            sequencer_program: Sequencer program to be uploaded
            timeout: Maximum time to wait for the compilation on the device in
                seconds. (default = 10s)

        Raises:
            TimeoutError: If the upload or compilation times out.
            RuntimeError: If the upload or compilation failed.
        """
        deviceutils.load_sequencer_program(
            self._daq_server,
            self._serial,
            self._index,
            sequencer_program,
            timeout=timeout,
        )

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
            raise RuntimeError(
                f"The device only has {self._max_qubits_per_channel} qubits per channel"
                f", but {max(pulses.keys())} where specified"
            )
        waveform_dict = {}
        if isinstance(pulses, Waveforms):
            for slot in pulses.keys():
                waveform_dict[slot] = pulses.get_raw_vector(slot, complex_output=True)
        else:
            waveform_dict = pulses

        deviceutils.write_to_waveform_memory(
            self._daq_server,
            self._serial,
            self._index,
            waveform_dict,
            clear_existing=clear_existing,
        )

    def read_from_waveform_memory(self, slots: t.List[int] = None) -> Waveforms:
        """Read pulses from the waveform memory.

        Args:
            slots: List of waveform indexes to read from the device. If not
                specified all assigned waveforms will be downloaded.

        Returns:
            Mutuable mapping of the downloaded waveforms.
        """
        nodes = []
        if slots is not None:
            for slot in slots:
                nodes.append(self.waveforms[slot].wave.node_info.path)
        else:
            nodes.append(self.waveforms["*"].wave.node_info.path)
        nodes = ",".join(nodes)
        waveforms_raw = self._daq_server.get(nodes, settingsonly=False, flat=True)
        waveforms = Waveforms()
        for slot, waveform in enumerate(waveforms_raw.values()):
            waveforms[slot] = waveform[0]["vector"]
        return waveforms

    def configure_sequencer_triggering(
        self, *, aux_trigger: str, play_pulse_delay: float = 0.0
    ) -> None:
        """Configure the sequencer triggering.

        Arguments:

            aux_trigger: Alias for the trigger source used in the sequencer.
                For the list of available values, use `available_aux_trigger_inputs`
            play_pulse_delay: Delay in seconds before the start of waveform playback.
        """
        # Only Digital Trigger 1
        deviceutils.configure_sequencer_triggering(
            self._daq_server,
            self._serial,
            self._index,
            aux_trigger=aux_trigger,
            play_pulse_delay=play_pulse_delay,
        )

    @property
    def available_aux_trigger_inputs(self) -> t.List[str]:
        """List of available aux trigger sources for the generator."""
        return [
            option.enum
            for option in self.auxtriggers[0].channel.node_info.options.values()
        ]
