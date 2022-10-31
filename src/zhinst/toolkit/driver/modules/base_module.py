"""Base Module Driver.

Natively works with all module types and provides the basic functionality like
the module specific nodetree.
"""
import logging
import time
import typing as t

from zhinst.core import ModuleBase
from zhinst.toolkit.nodetree import Node, NodeTree

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.driver.devices import DeviceType
    from zhinst.toolkit.session import Session

ZIModule = t.TypeVar("ZIModule", bound=ModuleBase)


class BaseModule(Node):
    """Generic toolkit driver for a LabOne Modules.

    All module specific class are derived from this class.
    It exposes the nodetree and also implements common functions valid for all
    modules.
    It also can be used directly, e.g. for modules that have no special class
    in toolkit.

    Args:
        raw_module: zhinst.core module.
        session: Session to the Data Server.
    """

    def __init__(self, raw_module: ZIModule, session: "Session"):
        self._raw_module = raw_module
        self._session = session
        super().__init__(NodeTree(raw_module), tuple())
        if "device" in self.root:
            self.root.update_nodes(
                {
                    "/device": {
                        "GetParser": self._get_device,
                        "SetParser": self._set_device,
                    }
                },
                raise_for_invalid_node=False,
            )

    def __repr__(self):
        return str(f"{self._raw_module.__class__.__name__}({repr(self._session)})")

    def _get_device(self, serial: str) -> t.Union["DeviceType", str]:
        """Convert a device serial into a toolkit device object.

        Args:
            serial: Serial of the device

        Returns:
            Toolkit device object. If the serial does not
                match to a connected device the serial is returned instead.
        """
        try:
            return self._session.devices[serial]
        except (RuntimeError, KeyError):
            return serial

    @staticmethod
    def _set_device(value: t.Union["DeviceType", str]) -> str:
        """Convert a toolkit device object into a serial string.

        Args:
            serial: A toolkit device object
                (can also be a serial string directly)

        Returns:
            str: device serial
        """
        try:
            return value.serial  # type: ignore
        except AttributeError:
            return value

    def _get_node(self, node: str) -> t.Union[Node, str]:
        """Convert a raw node string into a toolkit node.

        Args:
            node (str): raw node string

        Returns:
            Toolkit node. (if the node can not be converted the raw node
                string is returned)
        """
        try:
            return self._session.raw_path_to_node(node.replace(".", "/"), module=self)
        except (KeyError, RuntimeError):
            logger.error(
                f"Could not resolve {node} into a node of the "
                f"{self._raw_module.__class__.__name__} or "
                "a connected device."
            )
            return node

    @staticmethod
    def _set_node(signal: t.Union[Node, str]) -> str:
        """Convert a toolkit node into a raw node string.

        Args:
            signal: Toolkit node

        Returns:
            str: raw string node
        """
        try:
            node = signal.node_info.path  # type: ignore
        except AttributeError:
            node = signal
        return node

    def wait_done(self, *, timeout: float = 20.0, sleep_time: float = 0.5) -> None:
        """Waits until the module is finished.

        Warning: Only usable for modules that make use of the `/finished` node.

        Args:
            timeout (float): The maximum waiting time in seconds for the
                measurement (default: 20).
            sleep_time (int): Time in seconds to wait between
                requesting sweeper state. (default: 0.5)

        Raises:
            TimeoutError: The measurement is not completed before
                timeout.
        """
        start_time = time.time()
        while (
            start_time + timeout >= time.time()
            and not self._raw_module.finished()
            and self._raw_module.progress() != 1
        ):
            logger.info(f"Progress: {(self._raw_module.progress()[0] * 100):.1f}%")
            time.sleep(sleep_time)
        if not self._raw_module.finished() and self._raw_module.progress() != 1:
            raise TimeoutError(f"{self._raw_module.__class__.__name__} timed out.")
        logger.info(f"Progress: {(self._raw_module.progress()[0] * 100):.1f}%")

    def subscribe(self, signal: t.Union[Node, str]) -> None:
        """Subscribe to a node.

        The node can either be a node of this module or of a connected device.

        Args:
            signal: Node that should be subscribed to.

        .. versionchanged 0.5.0 Add support for raw string signals
        """
        try:
            self._raw_module.subscribe(signal.node_info.path)  # type: ignore
        except AttributeError:
            self._raw_module.subscribe(signal)

    def unsubscribe(self, signal: t.Union[Node, str]) -> None:
        """Unsubscribe from a node.

        The node can either be a node of this module or of a connected device.

        Args:
            signal: Node that should be unsubscribed from.

        .. versionchanged 0.5.0 Add support for raw string signals
        """
        try:
            self._raw_module.unsubscribe(signal.node_info.path)  # type: ignore
        except AttributeError:
            self._raw_module.unsubscribe(signal)

    def execute(self) -> None:
        """Start the module execution.

        Subscription or unsubscription is not possible until the execution is
        finished.

        .. versionadded:: 0.4.1
        """
        self._raw_module.execute()

    @property
    def raw_module(self) -> ZIModule:  # type: ignore [type-var]
        """Underlying core module."""
        return self._raw_module
