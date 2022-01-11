"""Zurich Instruments Toolkit (zhinst-toolkit) Command Table Module.

This module provides a :class:`CommandTable` class to create and modify ZI device
command tables.
"""

import copy
import json
import typing as t

import jsonref
import jsonschema

from zhinst.toolkit.exceptions import ValidationError

# JSON Schema validator for validating the schemes.
JSON_SCHEMA_VALIDATOR = jsonschema.Draft4Validator


def _validate_instance(instance, schema, validator=JSON_SCHEMA_VALIDATOR):
    try:
        jsonschema.validate(
            instance=instance,
            schema=schema,
            cls=validator,
        )
    except jsonschema.ValidationError as e:
        raise ValidationError(str(e)) from None


class ParentNode:
    """ParentNode of the command table.

    ParentNode can contain one or multiple arguments and child ParentNodes.
    It offers a dictionary-like object to manipulate command table properties.
    Similar to the device nodes, it supports accessing the properties by attribute.

    Args:
        schema: JSON schema of the node.
        path: Path representation of the node.
    """

    def __init__(self, schema: dict, path: t.Tuple[str, ...]):
        self._schema = schema
        self._path = path
        self._childs = {}

    def __repr__(self) -> str:
        return "/" + "/".join(self._path)

    def is_empty(self) -> bool:
        """Check if the Node is empty and has no properties.

        Returns:
            bool: If childs exists.
        """
        return not bool(self._childs)


class ParentEntry(ParentNode):
    """Parent entry of the CommandTable.

    The parent can have both properties and child properties.

    Args:
        schema: JSON schema of the node.
        path: Path representation of the node.
    """

    def __init__(self, schema: dict, path: t.Tuple[str, ...]):
        super().__init__(schema, path)
        self._attributes = {}
        self._child_props = {}
        self._properties = {}
        # ParentEntry does not have json list entries at this moment.
        for name, property_ in schema["properties"].items():
            if "properties" in property_:
                self._child_props[name] = property_
            else:
                self._attributes[name] = property_

    def __contains__(self, k):
        return k in self._child_props or self._attributes.get(k, None) is not None

    def __dir__(self):
        dir_info = set()
        for k in super().__dir__():
            if not k.startswith("_"):
                dir_info.add(k)
        return dir_info.union(set(list(self._schema["properties"].keys())))

    def __getattr__(self, name: str) -> t.Union["ParentEntry", t.Any]:
        if name.startswith("_"):
            return None
        try:
            return self._childs[name]
        except KeyError:
            if name in self._child_props:
                self._childs[name] = ParentEntry(
                    self._child_props[name], self._path + (name,)
                )
                return self._childs[name]
            if name in self._attributes:
                return self._properties.get(name, None)
        raise AttributeError(name)

    def __setattr__(self, name: str, value: t.Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        elif self._attributes and name in self._attributes:
            if value is None:
                self._childs.pop(name, None)
                self._properties.pop(name, None)
            else:
                _validate_instance(value, self._attributes[name])
                self._childs[name] = value
                self._properties[name] = value
        elif value is None and name in self._childs:
            self._childs.pop(name)
        else:
            raise AttributeError(name)

    def as_dict(self) -> dict:
        """Return a dictionary presentation of the table node.

        Returns:
            dict: Table node as dictionary.
        """
        result = {}
        for name, child in self._childs.items():
            if isinstance(child, (ParentEntry, HeaderEntry)):
                if not child.is_empty():
                    result[name] = child.as_dict()
                else:
                    continue
            else:
                result[name] = child
        return result

    def info(self, value: t.Optional[str] = None) -> dict:
        """Get info about the property.

        Args:
            value: Info about to specific property. Otherwise
                return info about the whole property.
        Returns:
            Info about the property.
        """
        return self._schema["properties"].get(value, None) if value else self._schema

    def clear(self) -> None:
        """Clear all properties from the object."""
        self._childs = {}
        self._properties = {}


class ListEntry(ParentNode):
    """List entry of a command table.

    Args:
        schema: JSON schema of the node.
        path: Path representation of the node.
    """

    def __init__(self, schema: dict, path: t.Tuple[str, ...]):
        super().__init__(schema, path)
        self._schema = copy.deepcopy(schema)
        self._min_length = schema["minItems"]
        self._max_length = schema["maxItems"]

        self._index_schema = schema["items"]["properties"]["index"]
        self._schema["items"]["properties"].pop("index", None)

    def __len__(self):
        return len(self._childs)

    def __getitem__(self, number: int) -> ParentEntry:
        _validate_instance(number, self._index_schema)
        try:
            return self._childs[number]
        except KeyError:
            self._childs[number] = ParentEntry(
                self._schema["items"], self._path + (str(number),)
            )
            return self._childs[number]

    def __delitem__(self, key):
        del self._childs[key]

    @property
    def range(self) -> t.Tuple[int, int]:
        """Get the range for number of minimum and maximum items in the table.

        Returns:
            Range for number of items in the table.
        """
        return (self._min_length, self._max_length)

    def as_list(self) -> t.List[dict]:
        """Return a list representation of the table.

        Returns:
            List of dictionary representation of entries in the table.
        """
        table = []
        for name, child in self._childs.items():
            if isinstance(child, ParentEntry):
                json_ = child.as_dict()
                if json_:
                    item = {"index": name}
                    item.update(json_)
                    table.append(item)
        return table


class HeaderEntry(ParentEntry):
    """Header entry of a command table.

    Args:
        schema: JSON schema of the node.
        path: Path representation of the node.
    """

    def __init__(self, schema: dict, path: tuple):
        super().__init__(schema, path)
        self._childs["version"] = schema["properties"]["version"]["enum"][-1]

    @property
    def version(self) -> str:
        """Version of the schema."""
        return self._childs["version"]


def _derefence_json(schema: t.Union[str, dict]) -> t.Any:
    """Dereference JSON schema.

    Args:
        schema: JSON schema as a string or dictionary.
    Returns:
        Dereferenced schema.
    Raises:
        ValueError: Wrong `schema` type.
    """
    if isinstance(schema, str):
        return jsonref.loads(schema, jsonschema=True)
    if isinstance(schema, dict):
        return jsonref.loads(json.dumps(schema), jsonschema=True)
    raise ValueError(schema)


class CommandTable:
    """A representation of a ZI device command table.

    The class provides functionality to create and modify existing
    command tables.

    The CommandTable can be modified by via ``header`` and ``table`` properties.

    Args:
        json_schema: JSON Schema of the command table.

    Example:

    .. code-block:: python

        from zhinst.toolkit import CommandTable

        ct = CommandTable(json_schema)

    The ``header`` and ``table`` and then be called.

    .. code-block:: python

        ct.header.version
        # "1.1"
        ct.header.userString = "My table"

        ct.table[0].amplitude.value = 1
        ct.table[0].amplitude
        # 1

        ct.as_json()
    """

    def __init__(self, json_schema: t.Union[str, dict]):
        self._ct_schema: t.Dict = _derefence_json(json_schema)
        self._header: HeaderEntry = self._header_entry()
        self._table: ListEntry = self._table_entry()

    @property
    def header(self) -> HeaderEntry:
        """Header of the built command table."""
        return self._header

    @property
    def table(self) -> ListEntry:
        """Table entry of the built command table."""
        return self._table

    def _header_entry(self):
        return HeaderEntry(self._ct_schema["definitions"]["header"], ("header",))

    def _table_entry(self):
        return ListEntry(self._ct_schema["definitions"]["table"], ("table",))

    def clear(self) -> None:
        """Clear CommandTable back to its initial state."""
        self._header = self._header_entry()
        self._table = self._table_entry()

    def as_dict(self) -> dict:
        """Return a dictionary representation of the :class:`CommandTable`.

        The function formats the returner value into a schema which is
        accepted by the ZI devices which support command tables.

        The table is validated against the given schema.

        Returns:
            CommandTable as a Python dictionary.

        Raises:
            :class:`~zhinst.toolkit.exceptions.ValidateError`: The command table
                does not correspond to the given JSON schema.
        """
        result = {
            "$schema": self._ct_schema["$schema"],
            "header": self._header.as_dict(),
            "table": self._table.as_list(),
        }
        _validate_instance(result, self._ct_schema)
        return result

    def update(self, command_table: t.Union[str, dict]) -> None:
        """Update the existing instance of ``CommandTable`` with command table JSON.

        If both command tables have the same properties, the existing ones
        are overwritted by the new command table.

        Args:
            command_table: Existing command table JSON.
        """

        def json_to_dict(json_: t.Union[str, t.Dict]) -> t.Dict:
            if isinstance(json_, str):
                json_ = json.loads(json_)
            return json_

        command_table = json_to_dict(copy.deepcopy(command_table))
        _validate_instance(command_table, self._ct_schema)

        def build_nodes(path: t.Optional[ParentEntry], index: int, obj: dict):
            for k, v in obj.items():
                if isinstance(v, dict):
                    build_nodes(getattr(path, k), index, v)
                else:
                    setattr(path, k, v)

        def build_header_nodes(header: HeaderEntry, obj: dict):
            for k, v in obj.items():
                if isinstance(k, dict):
                    build_header_nodes(getattr(header, k), v)
                else:
                    setattr(header, k, v)

        build_header_nodes(self._header, command_table["header"])

        for item in command_table["table"]:
            index = item.pop("index", None)
            build_nodes(self._table[index], index, item)
