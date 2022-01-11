""" zhinst-toolkit Command Table Node adaptions."""
import json
import typing as t
from functools import lru_cache
from pathlib import Path

from zhinst.toolkit.command_table import CommandTable
from zhinst.toolkit.nodetree import Node, NodeTree

_CT_RESOURCE_PATH = Path(__file__).parent.parent.parent / "resources"
_CT_FILES = {
    "shfsg": _CT_RESOURCE_PATH / "ct_schema_shfsg.json",
    "hdawg": _CT_RESOURCE_PATH / "ct_schema_hdawg.json",
}


class CommandTableNode(Node):
    """CommandTable node.

    This class implements the basic functionality of the command table allowing
    the user to load and upload their own command table.

    A dedicated class called ``CommandTable`` exists that is the prefered way
    to create a valid command table. For more information about the
    ``CommandTable`` refer to the corresponding example or the documentation
    of that class directly.

    Args:
        root: Node used for the upload of the command table
        tree: Tree (node path as tuple) of the current node
        device_type: Device type.
    """

    def __init__(self, root: NodeTree, tree: t.Tuple[str], device_type: str) -> None:
        Node.__init__(self, root, tree)
        self._device_type = device_type

    def check_status(self) -> bool:
        """Check status of the command table.

        Returns:
            Flag if a valid command table is loaded into the device.

        Raises:
            RuntimeError: If the command table upload into the device failed.
        """
        ct_status = self.status()
        if ct_status >> 3:
            raise RuntimeError(
                "Uploading of data to the command table failed due to a JSON parsing error"
            )
        return ct_status == 1

    @lru_cache()
    def load_validation_schema(self) -> dict:
        """Load device command table validation schema.

        Returns:
            JSON validation schema for the device command tables.
        """
        # TODO: Load from device once available.
        with open(_CT_FILES[self._device_type.lower()]) as f:
            return json.load(f)

    def upload_to_device(
        self, ct: t.Union[CommandTable, str, dict], *, validate: bool = True
    ) -> None:
        """Upload command table into the device.

        The command table can either be specified through the dedicated
        ``CommandTable`` class or in a raw format, meaning a json string or json
        dict. In the case of a json string or dict the command table is
        validated by default against the schema provided by the device.

        Args:
            ct: Command table.
            validate: Flag if the command table should be validated. (Only
                applies if the command table is passed as a raw json string or
                json dict)

        Raises:
            RuntimeError: If the command table upload into the device failed.
            zhinst.toolkit.exceptions.ValidationError: Incorrect schema.
        """
        try:
            self.data(json.dumps(ct.as_dict()))
        except AttributeError:
            if validate:
                ct_new = CommandTable(self.load_validation_schema())
                ct_new.update(ct)
                self.upload_to_device(ct_new)
            elif isinstance(ct, str):
                self.data(ct)
            else:
                self.data(json.dumps(ct))
        self.check_status()

    def load_from_device(self) -> CommandTable:
        """Load command table from the device.

        Returns:
            command table.
        """
        ct = CommandTable(self.load_validation_schema())
        ct.update(self.data())
        return ct
