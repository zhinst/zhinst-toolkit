"""Implements Connection wrapper around a native python dictionary."""
import fnmatch
import json
import re
import typing as t
from collections import OrderedDict

from numpy import array

from zhinst.toolkit.nodetree.helper import NodeDoc
from zhinst.toolkit.exceptions import ToolkitError


class ConnectionDict:
    """Connection wrapper around a dictionary.

    The ``NodeTree`` expects a connection that complies to the
    protocol :class:`nodetree.Connection`. In order to also support raw
    dictionaries this class wraps around a python dictionary and exposes the
    required protocol.

    Args:
        data: Dictionary raw path: value
        json_info: JSON information for each path (path: info)
    """

    def __init__(self, data: t.Dict[str, t.Any], json_info: NodeDoc):
        super().__init__()
        self._values = data
        self.json_info = json_info

    def _get_value(self, path: str) -> t.Any:
        """Return the value for a given path.

        If the value is callable it is called.

        Args:
            path: Key in the internal values dictionary.

        Returns:
            The value of the given path.
        """
        value = self._values[path]
        if callable(value):
            return value()
        return value

    def _resolve_wildcards(self, path: str) -> t.List[str]:
        path_raw = path.replace("/\\*/", "/[^/]*/")
        path_raw_regex = re.compile(path_raw)
        return list(filter(path_raw_regex.match, self._values.keys()))

    def _set_value(self, path: str, value: t.Any) -> None:
        """Set the value for a given path.

        If the value is callable it is called with the new value.

        Args:
            path: Key in the internal values dictionary.
            value: New value of the path.
        """
        paths = self._resolve_wildcards(path)
        if not paths:
            raise KeyError(path)
        for path in paths:
            self._do_set_value(path, value)

    def _do_set_value(self, path: str, value: t.Any) -> None:
        if callable(self._values[path]):
            self._values[path](value)
        else:
            self._values[path] = value

    def listNodesJSON(self, path: str, *args, **kwargs) -> str:
        """Returns a list of nodes with description found at the specified path."""
        if path == "*":
            return json.dumps(self.json_info)
        json_info = {}
        for node, info in self.json_info.items():
            if fnmatch.fnmatchcase(node, path + "*"):
                json_info[node] = info
        return json.dumps(json_info)

    def get(self, path: str, *args, **kwargs) -> t.Any:
        """Mirrors the behavior of zhinst.core get command."""
        nodes_raw = fnmatch.filter(self._values.keys(), path)
        if not nodes_raw:
            nodes_raw = fnmatch.filter(self._values.keys(), path + "*")
        return_value = OrderedDict()
        for node in nodes_raw:
            return_value[node] = array([self._get_value(node)])
        return return_value

    def getInt(self, path: str) -> int:
        """Mirrors the behavior of zhinst.core getInt command."""
        try:
            return int(self._get_value(path))
        except TypeError:
            if self._get_value(path) is None:
                return 0
            raise

    def getDouble(self, path: str) -> float:
        """Mirrors the behavior of zhinst.core getDouble command."""
        return float(self._get_value(path))

    def getString(self, path: str) -> str:
        """Mirrors the behavior of zhinst.core getDouble command."""
        return str(self._get_value(path))

    def _parse_input_value(self, path: str, value: t.Any):
        if isinstance(value, str):
            option_map = {}
            for key, option in self.json_info[path].get("Options", {}).items():
                node_options = re.findall(r'"(.+?)"[,:]+', option)
                option_map.update({x: int(key) for x in node_options})
            return option_map.get(value, value)
        return value

    def set(
        self,
        path: t.Union[str, t.List[t.Tuple[str, t.Any]]],
        value: t.Any = None,
        **kwargs,
    ) -> None:
        """Mirrors the behavior of zhinst.core set command."""
        if isinstance(path, str):
            self._set_value(path, self._parse_input_value(path, value))
        else:
            for node, node_value in path:
                self._set_value(node, self._parse_input_value(node, node_value))

    def setVector(self, path: str, value: t.Any = None) -> None:
        """Mirrors the behavior of zhinst.core setVector command."""
        self.set(path, value)

    def subscribe(self, path: str) -> None:
        """Mirrors the behavior of zhinst.core subscribe command."""
        raise ToolkitError("Can not subscribe within the SHFQA_Sweeper")

    def unsubscribe(self, path: str) -> None:
        """Mirrors the behavior of zhinst.core unsubscribe command."""
        raise ToolkitError("Can not subscribe within the SHFQA_Sweeper")
