# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
import json
import urllib
import jsonschema

from zhinst.toolkit.interface import LoggerModule

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
        try:
            request = urllib.request.Request(url=self._ct_schema_url)
            with urllib.request.urlopen(request) as f:
                self.ct_schema_dict = json.loads(f.read())
            version = self.ct_schema_dict["definitions"]["header"]["properties"][
                "version"
            ]["enum"]
            self.ct_schema_version = version[len(version) - 1]
        except Exception as ex:
            self.ct_schema_dict = None
            self.ct_schema_version = None
            _logger.warning(
                "The command table schema could not be downloaded from Zurich Instruments' server. "
                "Therefore, command tables cannot be validated against the schema by zhinst-toolkit itself. "
                "The automated check before upload is disabled."
                f"{ex}"
            )


    def load(self, table, validate=None):
        """Load a given command table to the instrument"""
        # Check if the input is a valid JSON
        table_updated = self._to_dict(table)
        if validate is None:
            validate = self.ct_schema_dict is not None
        if validate:
            if not self.ct_schema_dict:
                _logger.error(
                    "The command table schema is not available."
                    "The command table could not be validated.",
                    _logger.ExceptionTypes.ToolkitError,
                )
            self._validate(table_updated)
        # Convert the json object
        # Load the command table to the device
        node = self._node + "/data"
        self._device._set_vector(node, json.dumps(table_updated))

    def download(self):
        """Downloads a command table"""
        node = self._node + "/data"
        return self._device._get_vector(node)

    def _validate(self, table):
        """Ensure command table is valid JSON and compliant with schema"""
        # Validation only works if the command table is in dictionary
        # format (json object). Make the encessary conversion
        jsonschema.validate(
            table, schema=self.ct_schema_dict, cls=jsonschema.Draft4Validator
        )

    def _to_dict(self, table):
        """Check the input type and convert it to json object (dict)"""
        if isinstance(table, str):
            table_updated = json.loads(table)
        elif isinstance(table, list):
            table_updated = {
                "$schema": self._ct_schema_url,
                "table": table,
            }
            if self.ct_schema_version:
                table_updated["header"] = ({"version": self.ct_schema_version},)
        elif isinstance(table, dict):
            table_updated = table
        else:
            _logger.error(
                "The command table should be specified as either a string, or a list "
                "of entries without a header, or a valid json as a dictionary.",
                _logger.ExceptionTypes.ToolkitError,
            )
        return table_updated
