# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
import json
import urllib
import jsonschema

from zhinst.toolkit.interface import DeviceTypes, LoggerModule

_logger = LoggerModule(__name__)


class CommandTable:
    """Implement a CommandTable representation.

    The :class:`CommandTable` class implements the basic functionality
    of the command table allowing the user to write and upload their
    own command table.

    """

    def __init__(self, parent, ct_schema_url: str, ct_node: str) -> None:
        self._parent = parent
        self._index = self._parent._index
        self._device = self._parent._parent
        self._ct_schema_url = ct_schema_url
        self._node = ct_node
        with urllib.request.urlopen(self._ct_schema_url) as f:
            ct_schema_str = f.read().decode()
        self.ct_schema_dict = json.loads(ct_schema_str)

    def load(self, table):
        """Load a given command table to the instrument"""
        # Check if the input is a valid JSON
        table_updated = self._validate(table)
        # Convert the json object
        # Load the command table to the device
        node = self._node + "/data"
        self._device._set_vector(node, json.dumps(table_updated))

    def download(self):
        """Downloads a command table """
        node = self._node + "/data"
        return self._device._get_vector(node)

    def _validate(self, table):
        """Ensure command table is valid JSON and compliant with schema"""
        # Validation only works if the command table is in dictionary
        # format (json object). Make the encessary conversion
        table_updated = self._to_dict(table)
        jsonschema.validate(
            table_updated, schema=self.ct_schema_dict, cls=jsonschema.Draft4Validator
        )
        return table_updated

    def _to_dict(self, table):
        """Check the input type and convert it to json object (dict)"""
        if isinstance(table, str):
            table_updated = json.loads(table)
        elif isinstance(table, list):
            version = self.ct_schema_dict["definitions"]["header"]["properties"][
                "version"
            ]["enum"]
            version = version[len(version) - 1]
            table_updated = {
                "$schema": self._ct_schema_url,
                "header": {"version": version, "partial": False},
                "table": table,
            }
        elif isinstance(table, dict):
            table_updated = table
        else:
            _logger.error(
                "The command table should be specified as either a string, or a list "
                "of entries without a header, or a valid json as a dictionary.",
                _logger.ExceptionTypes.ToolkitError,
            )
        return table_updated
