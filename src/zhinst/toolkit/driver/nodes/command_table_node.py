"""Command Table Node adaptions."""
import json
import string
import typing as t
from pathlib import Path

from zhinst.toolkit.command_table import CommandTable
from zhinst.toolkit.nodetree import Node, NodeTree

_CT_RESOURCE_PATH = Path(__file__).parent.parent.parent / "resources"
_CT_FILES = {
    "shfqc": _CT_RESOURCE_PATH / "ct_schema_shfsg.json",
    "shfsg": _CT_RESOURCE_PATH / "ct_schema_shfsg.json",
    "hdawg": _CT_RESOURCE_PATH / "ct_schema_hdawg.json",
}


class CommandTableNode(Node):
    """CommandTable node.

    This class implements the basic functionality of the command table allowing
    the user to load and upload their own command table.

    A dedicated class called ``CommandTable`` exists that is the preferred way
    to create a valid command table. For more information about the
    ``CommandTable`` refer to the corresponding example or the documentation
    of that class directly.

    Args:
        root: Node used for the upload of the command table
        tree: Tree (node path as tuple) of the current node
        device_type: Device type.
    """

    def __init__(
        self, root: NodeTree, tree: t.Tuple[str, ...], device_type: str
    ) -> None:
        Node.__init__(self, root, tree)
        self._device_type = device_type
        self._schema: t.Optional[t.Dict[str, t.Any]] = None

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
                "Uploading of data to the command table failed "
                "due to a JSON parsing error."
            )
        return ct_status == 1

    def load_validation_schema(self) -> t.Dict[str, t.Any]:
        """Load device command table validation schema.

        Returns:
            JSON validation schema for the device command tables.
        """
        if self._schema is None:
            try:
                self._schema = json.loads(self.schema())
            except KeyError:
                device_type_striped = self._device_type.lower().rstrip(string.digits)
                with open(_CT_FILES[device_type_striped], encoding="utf-8") as file_:
                    self._schema = json.load(file_)
        return self._schema  # type: ignore

    def upload_to_device(
        self,
        ct: t.Union[CommandTable, str, dict],
        *,
        validate: bool = False,
        check_upload: bool = True,
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
            check_upload: Flag if the upload should be validated by calling
                `check_status`. This is not mandatory bat strongly recommended
                since the device does not raise an error when it rejects the
                command table. This Flag is ignored when called from within a
                transaction.

        Raises:
            RuntimeError: If the command table upload into the device failed.
            zhinst.toolkit.exceptions.ValidationError: Incorrect schema.

        .. versionchanged:: 0.4.2

            New Flag `check_upload` that makes the upload check optional.
            `check_status` is only called when not in a ongoing transaction.
        """
        try:
            self.data(json.dumps(ct.as_dict()))  # type: ignore
        except AttributeError:
            if validate:
                ct_new = CommandTable(self.load_validation_schema())
                ct_new.update(ct)
                self.upload_to_device(ct_new)
            elif isinstance(ct, str):
                self.data(ct)
            else:
                self.data(json.dumps(ct))
        if (
            check_upload
            and not self._root.transaction.in_progress()
            and not self.check_status()
        ):
            raise RuntimeError(
                "No valid command table reported by the device after upload."
            )

    def load_from_device(self) -> CommandTable:
        """Load command table from the device.

        Returns:
            command table.
        """
        ct = CommandTable(self.load_validation_schema(), active_validation=True)
        ct.update(self.data())
        return ct
