"""zhinst-toolkit AWG node adaptions."""

from __future__ import annotations

import json
import logging
import typing as t
from functools import cached_property

from zhinst.core import compile_seqc
from zhinst.toolkit.driver.nodes.command_table_node import CommandTableNode
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import (
    create_or_append_set_transaction,
)
from zhinst.toolkit.sequence import Sequence
from zhinst.toolkit.waveform import Waveforms

logger = logging.getLogger(__name__)


class AWG(Node):
    """AWG node.

    This class implements the basic functionality for the device specific
    arbitrary waveform generator.
    Besides the upload/compilation of sequences it offers the upload of
    waveforms and command tables.

    Args:
        root: Root of the nodetree
        tree: Tree (node path as tuple) of the current node
        session: Underlying session.
        serial: Serial of the device.
        index: Index of the corresponding awg channel
        device_type: Device type
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
        serial: str,
        index: int,
        device_type: str,
        device_options: str,
    ):
        Node.__init__(self, root, tree)
        self._daq_server = root.connection
        self._serial = serial
        self._index = index
        self._device_type = device_type
        self._device_options = device_options

    def enable_sequencer(self, *, single: bool) -> None:
        """Starts the sequencer of a specific channel.

        Warning:
            This function is synchronous and blocks until the sequencer is enabled.
            When working with multiple instruments this function is the wrong
            approach and the sequencer should be enabled asynchronously.
            (For more information please take a look at the awg example in the
            toolkit documentation.)

        Args:
            single: Flag if the sequencer should be disabled after finishing
            execution.

        Raises:
            RuntimeError: If the sequencer could not be enabled.
        """
        self.single(single)
        if not self.enable(1, deep=True):
            msg = (
                "The sequencer could not be enabled. Please ensure that the "
                "sequencer program is loaded and configured correctly."
            )
            raise RuntimeError(
                msg,
            )

    def wait_done(self, *, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the AWG is finished.

        Args:
            timeout: The maximum waiting time in seconds for the generator
                (default: 10).
            sleep_time: Time in seconds to wait between requesting generator
                state

        Raises:
            RuntimeError: If continuous mode is enabled
            TimeoutError: If the sequencer program did not finish within
                the specified timeout time
        """
        if not self.single():
            msg = (
                f"{self!r}: The generator is running in continuous mode, "
                "it will never be finished."
            )
            raise RuntimeError(
                msg,
            )
        try:
            self.enable.wait_for_state_change(0, timeout=timeout, sleep_time=sleep_time)
        except TimeoutError as error:
            msg = (
                f"{self!r}: The execution of the sequencer program did not finish "
                f"within the specified timeout ({timeout}s)."
            )
            raise TimeoutError(
                msg,
            ) from error

    def compile_sequencer_program(
        self,
        sequencer_program: t.Union[str, Sequence],
        **kwargs: t.Union[str, int],
    ) -> tuple[bytes, dict[str, t.Any]]:
        """Compiles a sequencer program for the specific device.

        Args:
            sequencer_program: The sequencer program to compile.

        Keyword Args:
            samplerate (int): Target sample rate of the sequencer. Only allowed/
                necessary for HDAWG devices. Must correspond to the samplerate
                used by the device (device.system.clocks.sampleclock.freq()).
                If not specified the function will get the value itself from
                the device. It is recommended passing the samplerate if more
                than one sequencer code is uploaded in a row to speed up the
                execution time.
            wavepath (str): path to directory with waveforms. Defaults to path used
                by LabOne UI or AWG Module.
            waveforms (str): waveform CSV files separated by ';'
            output (str): name of embedded ELF filename.

        Returns:
            elf: Binary ELF data for sequencer.
            extra: Extra dictionary with compiler output.

        Example:
            elf, compile_info = device.awgs[0].compile_sequencer_program(seqc)
            device.awgs[0].elf.data(elf)
            device.awgs[0].ready.wait_for_state_change(1)
            device.awgs[0].enable(True)


        Raises:
            RuntimeError: `sequencer_program` is empty.
            RuntimeError: If the compilation failed.
        """
        if "SHFQC" in self._device_type:
            kwargs["sequencer"] = "sg" if "sgchannels" in self._tree else "qa"
        elif "HDAWG" in self._device_type and "samplerate" not in kwargs:
            kwargs["samplerate"] = self.root.system.clocks.sampleclock.freq()

        return compile_seqc(
            str(sequencer_program),
            self._device_type,
            self._device_options,
            self._index,
            **kwargs,
        )

    def load_sequencer_program(
        self,
        sequencer_program: t.Union[str, Sequence],
        **kwargs: t.Union[str, int],
    ) -> dict[str, t.Any]:
        """Compiles the given sequencer program on the AWG Core.

        Warning:
            After uploading the sequencer program one needs to wait before for
            the awg core to become ready before it can be enabled.
            The awg core indicates the ready state through its `ready` node.
            (device.awgs[0].ready() == True)

        Args:
            sequencer_program: Sequencer program to be uploaded.

        Keyword Args:
            samplerate (int): Target sample rate of the sequencer. Only allowed/
                necessary for HDAWG devices. Must correspond to the samplerate
                used by the device (device.system.clocks.sampleclock.freq()).
                If not specified the function will get the value itself from
                the device. It is recommended passing the samplerate if more
                than one sequencer code is uploaded in a row to speed up the
                execution time.
            wavepath (str): path to directory with waveforms. Defaults to path used
                by LabOne UI or AWG Module.
            waveforms (str): waveform CSV files separated by ';'
            output (str): name of embedded ELF filename.

        Example:
            compile_info = device.awgs[0].load_sequencer_program(seqc)
            device.awgs[0].ready.wait_for_state_change(1)
            device.awgs[0].enable(True)

        Raises:
            RuntimeError: `sequencer_program` is empty.
            RuntimeError: If the upload or compilation failed.
        """
        elf, compiler_info = self.compile_sequencer_program(sequencer_program, **kwargs)
        self.elf.data(elf)
        return compiler_info

    def write_to_waveform_memory(
        self,
        waveforms: Waveforms,
        indexes: t.Optional[list] = None,
    ) -> None:
        """Writes waveforms to the waveform memory.

        The waveforms must already be assigned in the sequencer program.

        Args:
            waveforms: Waveforms that should be uploaded.
            indexes: Specify a list of indexes that should be uploaded. If
                nothing is specified all available indexes in waveforms will
                be uploaded. (default = None)
        """
        with create_or_append_set_transaction(self._root):
            for waveform_index in waveforms:
                if indexes and waveform_index not in indexes:
                    continue
                self.root.transaction.add(
                    self.waveform.waves[waveform_index],
                    waveforms.get_raw_vector(waveform_index),
                )

    def read_from_waveform_memory(
        self,
        indexes: t.Optional[list[int]] = None,
    ) -> Waveforms:
        """Read waveforms from the waveform memory.

        Args:
            indexes: List of waveform indexes to read from the device. If not
                specified all assigned waveforms will be downloaded.

        Returns:
            Waveform object with the downloaded waveforms.
        """
        waveform_info = json.loads(self.waveform.descriptors()).get("waveforms", [])
        nodes = [
            self.waveform.node_info.path + f"/waves/{index}"
            for index in range(len(waveform_info))
            if (indexes is None or index in indexes)
            # Entries that have a play_config equals to zero ar dummies/fillers
            # and can therefore be ignored.
            and int(waveform_info[index]["play_config"])
        ]
        nodes_str = ",".join(nodes)
        waveforms_raw = self._daq_server.get(nodes_str, settingsonly=False, flat=True)
        waveforms = Waveforms()
        for node, waveform in waveforms_raw.items():
            slot = int(node.rsplit("/", 1)[-1])
            waveforms.assign_native_awg_waveform(
                slot,
                waveform[0]["vector"],
                channels=int(waveform_info[slot].get("channels", 1)),
                markers_present=bool(int(waveform_info[slot].get("marker_bits")[0])),
            )
        return waveforms

    @cached_property
    def commandtable(self) -> t.Optional[CommandTableNode]:
        """Command table module.

        Returns:
            Command table module.
        """
        if self["commandtable"].is_valid():
            return CommandTableNode(
                self._root,
                (*self._tree, "commandtable"),
                self._device_type,
            )
        return None
