"""SHFSG Instrument Driver."""

import logging
import typing as t

import zhinst.utils.shfsg as utils

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.nodetree import Node
from zhinst.toolkit.nodetree.helper import lazy_property, not_callable_in_transactions
from zhinst.toolkit.nodetree.node import NodeList

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session


class AWGCore(AWG):
    """AWG Core Node."""

    def configure_marker_and_trigger(
        self,
        *,
        trigger_in_source: str,
        trigger_in_slope: str,
        marker_out_source: str,
    ) -> None:
        """Configures the trigger inputs and marker outputs of the AWG.

        Args:
            trigger_in_source: Alias for the trigger input used by the
                sequencer. For a list of available values use:
                `available_trigger_inputs`
            trigger_in_slope: Alias for the slope of the input trigger
                used by sequencer. For a list of available values use
                `available_trigger_inputs`
            marker_out_source: Alias for the marker output source used by
                the sequencer. For a list of available values use
                `available_trigger_slopes`
        """
        settings = utils.get_marker_and_trigger_settings(
            self._serial,
            self._index,
            trigger_in_source=trigger_in_source,
            trigger_in_slope=trigger_in_slope,
            marker_out_source=marker_out_source,
        )
        self._send_set_list(settings)

    @property
    def available_trigger_inputs(self) -> t.List[str]:
        """List the available trigger sources for the sequencer."""
        return [
            option.enum
            for option in self.auxtriggers[0].channel.node_info.options.values()
        ]

    @property
    def available_trigger_slopes(self) -> t.List[str]:
        """List the available trigger slopes for the sequencer."""
        return [
            option.enum
            for option in self.auxtriggers[0].slope.node_info.options.values()
        ]

    @property
    def available_marker_outputs(self) -> t.List[str]:
        """List the available trigger marker outputs for the sequencer."""
        return [
            option.enum
            for option in self.root.sgchannels[
                self._index
            ].marker.source.node_info.options.values()
        ]


class SGChannel(Node):
    """Signal Generator Channel for the SHFSG.

    :class:`SGChannel` implements basic functionality to configure SGChannel
    settings of the :class:`SHFSG` instrument.

    Args:
        device: SHFQA device object.
        session: Underlying session.
        tree: Node tree (node path as tuple) of the corresponding node.
    """

    def __init__(
        self,
        device: "SHFSG",
        session: "Session",
        tree: t.Tuple[str, ...],
    ):
        super().__init__(device.root, tree)
        self._index = int(tree[-1])
        self._device = device
        self._serial = device.serial
        self._session = session

    @not_callable_in_transactions
    def configure_channel(
        self,
        *,
        enable: bool,
        output_range: int,
        center_frequency: float,
        rf_path: bool,
    ) -> None:
        """Configures the RF input and output.

        Args:
            enable: Flag if the signal output should be enabled.
            output_range: Maximal range of the signal output power in dBm
            center_frequency: Center frequency before modulation
            rf_path: Flag if the RF(True) or LF(False) path should be
                configured.
        """
        utils.configure_channel(
            self._session.daq_server,
            self._device.serial,
            self._index,
            enable=int(enable),
            output_range=output_range,
            center_frequency=center_frequency,
            rflf_path=int(rf_path),
        )

    def configure_pulse_modulation(
        self,
        *,
        enable: bool,
        osc_index: int = 0,
        osc_frequency: float = 100e6,
        phase: float = 0.0,
        global_amp: float = 0.5,
        gains: tuple = (1.0, -1.0, 1.0, 1.0),
        sine_generator_index: int = 0,
    ) -> None:
        """Configure the pulse modulation.

        Configures the sine generator to digitally modulate the AWG output, for
        generating single sideband AWG signals

        Args:
            enable: Flag if the modulation should be enabled.
            osc_index: Selects which oscillator to use
            osc_frequency: Oscillator frequency used to modulate the AWG
                outputs. (default = 100e6)
            phase: Sets the oscillator phase. (default = 0.0)
            global_amp: Global scale factor for the AWG outputs. (default = 0.5)
            gains: Sets the four amplitudes used for single sideband generation.
                Default values correspond to upper sideband with a positive
                oscillator frequency. (default = (1.0, -1.0, 1.0, 1.0))
            sine_generator_index: Selects which sine generator to use on a
                given channel.
        """
        settings = utils.get_pulse_modulation_settings(
            self._device.serial,
            self._index,
            enable=int(enable),
            osc_index=osc_index,
            osc_frequency=osc_frequency,
            phase=phase,
            global_amp=global_amp,
            gains=gains,
            sine_generator_index=sine_generator_index,
        )

        self._send_set_list(settings)

    def configure_sine_generation(
        self,
        *,
        enable: bool,
        osc_index: int = 0,
        osc_frequency: float = 100e6,
        phase: float = 0.0,
        gains: tuple = (0.0, 1.0, 1.0, 0.0),
        sine_generator_index: int = 0,
    ) -> None:
        """Configures the sine generator output.

        Configures the sine generator output of a specified channel for generating
        continuous wave signals without the AWG.

        Args:
            enable: Flag if the sine generator output should be enabled.
            osc_index: Selects which oscillator to use
            osc_frequency: Oscillator frequency used by the sine generator
                (default = 100e6)
            phase: Sets the oscillator phase. (default = 0.0)
            gains: Sets the four amplitudes used for single sideband
                generation. Default values correspond to upper sideband with a
                positive oscillator frequency.
                Gains are set in the following order I/sin, I/cos, Q/sin, Q/cos.
                (default = (0.0, 1.0, 1.0, 0.0))
            sine_generator_index: Selects which sine generator to use on a given
                channel
        """
        settings = utils.get_sine_generation_settings(
            self._device.serial,
            self._index,
            enable=int(enable),
            osc_index=osc_index,
            osc_frequency=osc_frequency,
            phase=phase,
            gains=gains,
            sine_generator_index=sine_generator_index,
        )

        self._send_set_list(settings)

    @property
    def awg_modulation_freq(self) -> float:
        """Modulation frequency of the AWG.

        Depends on the selected oscillator.
        """
        selected_osc = self.sines[0].oscselect()
        return self.oscs[selected_osc].freq()

    @lazy_property
    def awg(self) -> AWGCore:
        """AWG."""
        return AWGCore(
            self._root,
            self._tree + ("awg",),
            self._device.serial,
            self._index,
            self._device.device_type,
            self._device.device_options,
        )


class SHFSG(BaseInstrument):
    """High-level driver for the Zurich Instruments SHFSG."""

    @lazy_property
    def sgchannels(self) -> t.Sequence[SGChannel]:
        """A Sequence of SG Channels."""
        return NodeList(
            [
                SGChannel(self, self._session, self._tree + ("sgchannels", str(i)))
                for i in range(len(self["sgchannels"]))
            ],
            self._root,
            self._tree + ("sgchannels",),
        )
