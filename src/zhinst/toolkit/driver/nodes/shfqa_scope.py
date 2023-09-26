"""zhinst-toolkit scope node adaptions for the SHFQA."""
import logging
import typing as t

import zhinst.utils.shfqa as utils
from zhinst.core import ziDAQServer

from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import not_callable_in_transactions

logger = logging.getLogger(__name__)


class SHFScope(Node):
    """SHFQA Scope Node.

    Implements basic functionality of the scope node, e.g allowing the user to
    read the data.

    Args:
        root: Root of the nodetree
        tree: Tree (node path as tuple) of the current node
        daq_server: Instance of the ziDAQServer
        serial: Serial of the device.
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
        daq_server: ziDAQServer,
        serial: str,
    ):
        super().__init__(root, tree)
        self._daq_server = daq_server
        self._serial = serial

    def run(
        self, *, single: bool = True, timeout: float = 10, sleep_time: float = 0.005
    ) -> None:
        """Run the scope recording.

        Args:
            timeout: The maximum waiting time in seconds for the Scope
                (default = 10).
            sleep_time: Time in seconds to wait between requesting the progress
                and records values (default = 0.005).

        Raises:
            TimeoutError: The scope did not start within the specified
                timeout.
        """
        self.single(single)
        self.enable(True)
        try:
            self.enable.wait_for_state_change(1, timeout=timeout, sleep_time=sleep_time)
        except TimeoutError as error:
            raise TimeoutError(
                "Scope could not been started within "
                f"the specified timeout ({timeout})s"
            ) from error

    def stop(self, *, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Stop the scope recording.

        Args:
            timeout: The maximum waiting time in seconds for the scope
                (default = 10).
            sleep_time: Time in seconds to wait between requesting the progress
                and records values (default = 0.005).

        Raises:
            TimeoutError: The scope did not stop within the specified
                timeout.
        """
        self.enable(False)
        try:
            self.enable.wait_for_state_change(0, timeout=timeout, sleep_time=sleep_time)
        except TimeoutError as error:
            raise TimeoutError(
                "Scope could not been stopped within "
                f"the specified timeout ({timeout})s"
            ) from error

    def wait_done(self, *, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until the scope recording is finished.

        Args:
            timeout: The maximum waiting time in seconds for the Scope
                (default = 10).
            sleep_time: Time in seconds to wait between requesting the progress
                and records values (default = 0.005).

        Raises:
            TimeoutError: The scope did not finish within the specified
                timeout.
        """
        try:
            self.enable.wait_for_state_change(0, timeout=timeout, sleep_time=sleep_time)
        except TimeoutError as error:
            raise TimeoutError(
                "Scope recording did not finish "
                f"within the specified timeout({timeout})s."
            ) from error

    def configure(
        self,
        *,
        input_select: t.Dict[int, str],
        num_samples: int,
        trigger_input: str,
        num_segments: int = 1,
        num_averages: int = 1,
        trigger_delay: float = 0,
    ) -> None:
        """Configures the scope for a measurement.

        Args:
            input_select: Map of a specific scope channel an their signal
                source, e.g. "channel0_signal_input". (For a list of available
                values use `available_inputs`)
            num_samples: Number samples to recorded in a scope shot.
            trigger_input: Specifies the trigger source of the scope
                acquisition - if set to None, the self-triggering mode of the
                scope becomes active, which is useful e.g. for the GUI.
                For a list of available trigger values use
                `available_trigger_inputs`.
            num_segments: Number of distinct scope shots to be returned after
                ending the acquisition.
            num_averages: Specifies how many times each segment should be
                averaged on hardware; to finish a scope acquisition, the number
                of issued triggers must be equal to num_segments * num_averages.
            trigger_delay: delay in samples specifying the time between the
                start of data acquisition and reception of a trigger.
        """
        settings = utils.get_scope_settings(
            self._serial,
            input_select=input_select,
            num_samples=num_samples,
            trigger_input=trigger_input,
            num_segments=num_segments,
            num_averages=num_averages,
            trigger_delay=trigger_delay,
        )
        self._send_set_list(settings)

    @not_callable_in_transactions
    def read(
        self,
        *,
        timeout: float = 10,
    ) -> tuple:
        """Read out the recorded data from the scope.

        Args:
            timeout: The maximum waiting time in seconds for the
                Scope (default: 10).

        Returns:
            (recorded_data, recorded_data_range, scope_time)

        Raises:
            TimeoutError: if the scope recording is not completed before
                timeout.
        """
        return utils.get_scope_data(self._daq_server, self._serial, timeout=timeout)

    @property
    def available_trigger_inputs(self) -> t.List[str]:
        """List of the available trigger sources for the scope."""
        return [
            option.enum for option in self.trigger.channel.node_info.options.values()
        ]

    @property
    def available_inputs(self) -> t.List[str]:
        """List of the available signal sources for the scope channels."""
        return [
            option.enum
            for option in self.channels[0].inputselect.node_info.options.values()
        ]
