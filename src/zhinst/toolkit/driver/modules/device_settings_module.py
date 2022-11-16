"""Device Settings Module."""

import logging
import typing as t
from pathlib import Path

from zhinst.core import DeviceSettingsModule as ZIDeviceSettingsModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

from zhinst.toolkit.nodetree.helper import NodeDict

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.driver.devices import DeviceType
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class DeviceSettingsModule(BaseModule):
    """Implements the device settings module for storing and loading settings.

    The Device Settings Module provides functionality for saving and loading
    device settings to and from file. The file is saved in XML format.

    For simple save and load two helper functions exist `save_to_file` and
    `load_from_file`.

    Note: It is not recommend to use this function to read the
        device settings. Instead one can use the zhinst-toolkit functionality
        to read all settings from a device/subtree from the device directly by
        calling it.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_programming_manual/device_settings_module.html

    Args:
        device_settings_module: Instance of the core Impedance Module.
        session: Session to the Data Server.
    """

    def __init__(
        self, device_settings_module: ZIDeviceSettingsModule, session: "Session"
    ):
        super().__init__(device_settings_module, session)
        self.root.update_nodes(
            {
                "/path": {
                    "SetParser": self._set_path,
                }
            },
            raise_for_invalid_node=False,
        )

    def _simple_execution(
        self,
        command: str,
        filename: t.Union[str, Path],
        device: t.Union[str, "DeviceType"],
        timeout: float = 30,
    ) -> None:
        """Execute a command on a clean module.

        This function creates an new module instance to avoid misconfiguration.
        It is also synchronous, meaning it will block until command has
        finished.

        Args:
            command:  The command to execute. (`save`, `load`, `read`)
            filename: The path to the settings file.
            device: The device to load the settings to.
            timeout: Max time to wait for the loading to finish.

        Raises:
            TimeoutError: If the loading of the settings timed out.
        """
        filename = Path(filename)
        temp_module = self._session.modules.create_device_settings_module()
        temp_module.device(device)
        temp_module.filename(filename.stem)
        temp_module.path(filename.parent)
        temp_module.command(command)
        temp_module.execute()
        try:
            # Use finish node instead of function to make advantage of the
            # wait for state change functionality.
            temp_module.finished.wait_for_state_change(1, timeout=timeout)
        except TimeoutError as e:
            raise TimeoutError(
                f"Unable to load device settings after {timeout} seconds."
            ) from e

    def load_from_file(
        self,
        filename: t.Union[str, Path],
        device: t.Union["DeviceType", str],
        timeout: float = 30,
    ) -> None:
        """Load a LabOne settings file to a device.

        This function creates an new module instance to avoid misconfiguration.
        It is also synchronous, meaning it will block until loading the
        settings has finished.

        Args:
            filename: The path to the settings file.
            device: The device to load the settings to.
            timeout: Max time to wait for the loading to finish.

        Raises:
            TimeoutError: If the loading of the settings timed out.
        """
        self._simple_execution("load", filename, device, timeout)

    def save_to_file(
        self,
        filename: t.Union[str, Path],
        device: t.Union["DeviceType", str],
        timeout: int = 30,
    ) -> None:
        """Save the device settings to a LabOne settings file.

        This function creates an new module instance to avoid misconfiguration.
        It is also synchronous, meaning it will block until save operation has
        finished.

        Args:
            filename: The path to the settings file.
            device: The device which settings should be saved.
            timeout: Max time to wait for the loading to finish.

        Raises:
            TimeoutError: If the loading of the settings timed out.
        """
        self._simple_execution("save", filename, device, timeout)

    def read(self) -> NodeDict:
        """Read device settings.

        Note: It is not recommend to use this function to read the
        device settings. Instead one can use the zhinst-toolkit functionality
        to read all settings from a device/subtree from the device directly by
        calling it.

        >>> device = session.connect_device()
        >>> ...
        >>> device()
        <all device settings>
        >>> device.demods()
        <all demodulator settings>

        Returns:
            Device settings.
        """
        return super().read()
