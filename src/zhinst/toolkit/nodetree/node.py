"""Single lazy node of a :class:`zhinst.toolkit.nodetree.Nodetree`."""

import fnmatch
import json
import numbers
import re
import time
import typing as t
from collections import namedtuple
from collections.abc import Sequence
from enum import IntEnum
import numpy as np

from zhinst.toolkit.nodetree.helper import (
    NodeDict,
    lazy_property,
    resolve_wildcards_labone,
)

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.nodetree import NodeTree


class NodeEnumMeta:
    """Custom Metaclass for NodeEnum.

    Note: Required to enable pickling of a NodeEnum value.

    It simply servers the purpose to recreate a NodeEnum for a given enum
    value. Since the NodeEnums are created dynamically there is no way recreate
    a NodeEnum value since python can not find the definition. This class
    bypasses this problem by providing the functionality to recreate the
    Enum on the fly.

    Warning: Although the class of the resulting enum object looks and feels
    the same as the original one it is not. Therefore comparing the `type` will
    fail. This is however the only limitation.
    (type(value_old) != type(value_new) but value_old == value_new)

    Args:
        value: Value of the NodeEnum object that should be created.
        class_name: Name of the NodeEnum class.
        names: Mapping of the enum names to their corresponding integer value.
        module: Should be set to the module this class is being created in.
    """

    def __new__(  # noqa: D102
        cls, value: int, class_name: str, names: t.Dict[str, int], module: str
    ):
        new_enum = NodeEnum(class_name, names, module=module)
        return new_enum(value)


class NodeEnum(IntEnum):
    """Custom dynamically picklable IntEnum class.

    The Enum values for a device are created dynamically in toolkit based on
    the node informations. Since they are not predefined but rather created
    dynamically, the are not picklable. This custom child class of IntEnum
    overwrites the reduce function that returns all information required to
    recreate the Enum class in `NodeEnumMeta`.

    For more information on the reduce functionality and how it is used within
    the pickle package see
    [pep307](https://peps.python.org/pep-0307/#extended-reduce-api).
    """

    # Required for typing
    def __init__(self, *args, **kwargs):
        ...

    # Required for typing
    def __call__(self, *args, **kwargs):  # noqa: D102 # pragma: no cover
        ...

    def __reduce_ex__(self, _):
        return NodeEnumMeta, (
            self._value_,
            self.__class__.__name__,
            {key: int(value) for key, value in self.__class__._member_map_.items()},
            self.__class__.__module__,
        )


class NodeInfo:
    """Class that holds the additional information for a single node.

    LabOne provides for each leaf node a dictionary of so called node info
    (In addition toolkit or the user may also add some information for selected
    nodes). This class wraps around these information and exposes them to a user
    in a friendly way.

    During the initialization is fetches the relevant information from the
    root of the nodetree and stores them internally.

    Args:
        node: A node the information belong to.

    .. versionchanged:: 0.5.0

        Add support for signals in sample nodes. The daq module of LabOne
        supports subscribing to signals of samples nodes directly. They can be
        specified by appending them with a dot to the node path
        (e.g. /dev1234/demods/0/sample.x). The change now support these signals
        natively in the nodetree.
    """

    def __init__(self, node: "Node"):
        self._info = {}
        self._is_wildcard = False
        self._is_partial = False
        if any(wildcard in "".join(node.raw_tree) for wildcard in ["*", "?", "["]):
            self._info = {"Node": node.root.node_to_raw_path(node)}
            self._is_wildcard = True
        else:
            try:
                self._info = next(iter(node.root.get_node_info_raw(node).values()))
                self._info["Node"] = self._info.get(
                    "Node", node.root.node_to_raw_path(node)
                ).lower()
            except KeyError as error:
                self._info = {"Node": error.args[0]}
                if "sample" in node.raw_tree and "sample" != node.raw_tree[-1]:
                    path, signal = self._info["Node"].split("/sample/")
                    self._info["Node"] = path + "/sample." + ".".join(signal.split("/"))
                if self._check_partial(node):
                    self._is_partial = True
                if self._check_dynamic(node):
                    self._info.update(
                        json.loads(
                            node.root.connection.listNodesJSON(error.args[0])
                        ).get(error.args[0], {})
                    )

    def __dir__(self):
        dir_info = []
        for var, value in vars(self.__class__).items():
            if isinstance(value, property) and not var.startswith("_"):
                dir_info.append(var)
        return dir_info

    def __repr__(self) -> str:
        node_type = "partial" if self.is_partial else "leaf"
        node_type = "wildcard" if self.contains_wildcards else node_type
        return f'NodeInfo("{self.path}",{node_type}-node)'

    def __str__(self) -> str:
        string = self.path
        if self.is_partial:
            return string + "\nPartial node"
        if self._is_wildcard:
            return string + "\nContains wildcards"
        if "Description" in self._info:
            string += "\n" + self._info["Description"]
        for key, value in self._info.items():
            if key == "Options":
                string += f"\n{key}:"
                for option, description in value.items():
                    string += f"\n    {option}: {description}"
            elif key not in ["Description", "Node", "SetParser", "GetParser"]:
                string += f"\n{key}: {value}"
        return string

    def __getitem__(self, item: str) -> t.Union[str, t.Dict[str, str]]:
        return self._info[item]

    def __contains__(self, k):
        return k in self._info

    def __hash__(self):
        return hash(self.path + "NodeInfo")

    def __eq__(self, other):
        return self._info == other._info

    T = t.TypeVar("T")

    def set_parser(self, value: T) -> T:
        """Parse the set value."""
        try:
            _parser = self._info["SetParser"]
            if isinstance(_parser, list):
                for parser in _parser:
                    value = parser(value)
                return value
            return _parser(value)
        except KeyError:
            return value

    def get_parser(self, value: T) -> T:
        """Parse the get value."""
        try:
            _parser = self._info["GetParser"]
            if isinstance(_parser, list):
                for parser in _parser:
                    value = parser(value)
                return value
            return _parser(value)
        except KeyError:
            return value

    @staticmethod
    def _check_partial(node: "Node") -> bool:
        """Flag if the node is a partial node."""
        for child_node, _ in node.root:
            if node.is_child_node(child_node) and node != child_node:
                return True
        return False

    @staticmethod
    def _check_dynamic(node: "Node") -> bool:
        try:
            return node.raw_tree[-2] == "waves"
        except IndexError:
            return False

    @property
    def is_partial(self) -> bool:
        """Flag if the node is a partial node (non-leaf node)."""
        return self._is_partial

    @property
    def contains_wildcards(self) -> bool:
        """Flag if the node contains wildcards."""
        return self._is_wildcard

    @property
    def readable(self) -> t.Optional[bool]:
        """Flag if the node is readable.

        Returns None if the node does not provide the information (e.g. wildcard
        or partial nodes.)
        """
        try:
            return "Read" in self._info["Properties"]
        except KeyError:
            return None

    @property
    def writable(self) -> t.Optional[bool]:
        """Flag if the node is writable.

        Returns None if the node does not provide the information (e.g. wildcard
        or partial nodes.)
        """
        try:
            return "Write" in self._info["Properties"]
        except KeyError:
            return None

    @property
    def is_setting(self) -> t.Optional[bool]:
        """Flag if the node is setting node.

        Returns None if the node does not provide the information (e.g. wildcard
        or partial nodes.)
        """
        try:
            return "Setting" in self._info["Properties"]
        except KeyError:
            return None

    @property
    def is_vector(self) -> t.Optional[bool]:
        """Flag if the value of the node a vector.

        Returns None if the node does not provide the information (e.g. wildcard
        or partial nodes.)
        """
        try:
            return "Vector" in self._info["Type"]
        except KeyError:
            return None

    @property
    def path(self) -> str:
        """Path (LabOne representation) of the node."""
        return self._info["Node"]

    @property
    def description(self) -> str:
        """Description of the node."""
        return self._info["Description"]

    @property
    def type(self) -> str:
        """Type of the node."""
        return self._info["Type"]

    @property
    def unit(self) -> str:
        """Unit of the node."""
        return self._info["Unit"]

    _option_info = namedtuple("_option_info", ["enum", "description"])

    @lazy_property
    def options(self) -> t.Dict[int, _option_info]:
        """Options of the node."""
        option_map = {}
        for key, value in self._info.get("Options", {}).items():
            # Find all the keywords. We use only the first one
            # since it should be unambiguous
            enum_re = re.findall(r'"([a-zA-Z0-9-_"]+)"', value)
            enum = enum_re[0] if enum_re else ""

            # The description is either what comes after
            # the colon and space, or the whole string.
            # This is the case for nameless options, when the
            # key is an integer (for example demods/x/order)
            desc = re.findall(r'(?:.+":\s)?(.+)$', value)[0]

            option_map[int(key)] = self._option_info(enum, desc)
        return option_map

    @lazy_property
    def enum(self) -> t.Optional[NodeEnum]:
        """Enum of the node options."""
        options_reversed = {}
        for int_key, value in self._info.get("Options", {}).items():
            # Find all the keywords associated to a integer key
            enum_re = re.finditer(r'"(?P<keyword>[a-zA-Z0-9-_"]+)"', value)
            for m in enum_re:
                keyword = m.group("keyword")
                options_reversed[keyword] = int_key

        return (
            NodeEnum(self.path, options_reversed, module=__name__)
            if options_reversed
            # Nameless options do not have a enum.
            else None
        )


class Node:
    """Lazy node of a ``Nodetree``.

    The node is implemented in a lazy way. Meaning unless operations are not
    performed on the node, no checks whether the node is valid or not are
    performed.

    The child nodes of each node can be accessed in the same way than on the
    Nodetree, either by attribute or by item.

    The core functionality of each node is the overloaded call operator.
    Making a call gets the value(s) for that node. Passing a value to the call
    operator will set that value to the node on the device. Calling a node that
    is not a leaf (wildcard or partial node) will return/set the value on every
    node that matches it (the return type will be a dictionary).

    Warning:
        Setting a value to a non-leaf node will try to set the value of all
        nodes that matches that node. It should therefor be used with great care
        to avoid unintentional changes.

    >>> nodetree.demods[0].freq()
    1000
    >>> nodetree.demods[0].freq(2000)
    >>> nodetree.demods[0].freq()
    2000

    >>> nodetree.demods["*"].freq(3000)
    >>> nodetree.demods["*"].freq()
    {
        '/dev1234/demods/0/freq': 3000
        '/dev1234/demods/1/freq': 3000
        '/dev1234/demods/2/freq': 3000
        '/dev1234/demods/3/freq': 3000
    }

    .. versionchanged:: 0.3.5

        Call operator returns `WildcardResult` when wildcards are used in
        getting values.

    .. versionchanged:: 0.5.0 Returns NodeDict instead of WildcardResult

    The call operator supports the following flags:

    * deep: Flag if the set operation should be blocking until the data
        has arrived at the device, respectively if the get operation should
        return the value from the device or the cached value on the data
        server (if there is any). If this flag is set the operation can
        take significantly longer. (default = False)

        For a deep get operation the timestamp from the device is returned
        in addition to the value (The timestamp can be None, e.g. deep gets
        on LabOne modules).

        >>> nodetree.demods[0].freq(deep=True)
        (343283971893, 2000)

        For a deep set the call operator will return the value acknowledged
        by the device. e.g. important for floating point values with a
        limited resolution.

        >>> nodetree.demods[0].freq(29999,99999, deep=True)
        3000

    Warning:
        The deep flag does not work for wildcard nodes or non leaf nodes since
        they represent multiple nodes that are set in a transactional set which
        does not report the acknowledged values.

    * enum: Flag if enumerated values should return the enum value as
        string. (default = True)

    * parse: Flag if the SetParser/GetParser from the Node, if present,
        should be applied or not (default = True).

        The parsers are hard coded lambda functions provided not directly by
        LabOne but need to be set manually (e.g. toolkit adds these for a
        selected set of nodes). The Lambda function gets called right
        before/after the API call to LabOne. Usually they are used to add
        additional limitations and improve error reporting but in theory they
        can be used for anything.

        To add a parser to a node use the ``NodeTree.update_node`` function.

        >>> nodetree.update_node(
                "/dev1234/demods/0/freq",
                {
                    "GetParser": lambda v: print(f"got {v} from LabOne") return v,
                    "SetParser": lambda v: print(f"set {v} to LabOne") return v,
                },
            )

    In addition to the call operator the following magic methods are
    implemented:

    * __contains__
        >>> "freq" in nodetree.demods[0]
        True
    * __iter__
        >>> for node, info in nodetree.demods["*"].freq
    * __eq__
        >>> nodetree.demods[0].freq == nodetree.demods["*/freq"]
    * __len__ (only implemented for list like nodes)
        >>> len(nodetree.demods)
        4
    * __bool__ test if the node is a existing node
        >>> if nodetree.demods[0].freq:
            ...
    * __hash__ (e.g. necessary to be able to use nodes as key in dictionaries)

    Args:
        root: Root of the nodetree.
        tree: Tree (node path as tuple) of the current node.
    """

    def __init__(self, root: "NodeTree", tree: tuple):
        self._root = root
        self._tree = tree
        self._is_valid: t.Optional[bool] = None

    def __getattr__(self, name) -> "Node":
        return Node(self._root, self._tree + (name,))

    def __getitem__(self, name) -> "Node":
        name = str(name).lower()
        if "/" in name:
            name_list = name.split("/")
            if name_list[0]:
                return Node(self._root, self._tree + (*name_list,))
            return Node(self._root, self._tree + (*name_list[1:],))
        return Node(self._root, self._tree + (name,))

    def __contains__(self, k):
        return k in self._next_layer

    def __iter__(self):
        for child_node, info in self._root:
            if self.is_child_node(child_node):
                yield child_node, info

    def __repr__(self):
        return self.node_info.path

    def __dir__(self):
        dir_info = list(self._next_layer)
        for var, value in vars(self.__class__).items():
            if (
                isinstance(value, property)
                and not var.startswith("_")
                and var not in dir_info
            ):
                dir_info.append(var)
        return dir_info

    def __eq__(self, other):
        # buildin keywords are escaped with a tailing underscore
        # (https://pep8.org/#descriptive-naming-styles)
        own_node_list = tuple(node.rstrip("_") for node in self._tree)
        other_node_list = tuple(node.rstrip("_") for node in other.raw_tree)
        return own_node_list == other_node_list and self._root is other._root

    def __hash__(self):
        own_node_list = tuple(node.rstrip("_") for node in self._tree)
        if not own_node_list:
            own_node_list = "Node"
        return hash((own_node_list, repr(self._root)))

    def __bool__(self):
        return self.is_valid()

    def __len__(self):
        if not self._is_list():
            raise TypeError(f"Node {self.node_info.path} is not a list")
        return len(self._next_layer)

    def __call__(
        self, value: t.Any = None, *, deep=False, enum=True, parse=True, **kwargs
    ) -> t.Any:
        """Call operator that either gets (empty) or gets the value of a node.

        Args:
            value: Optional value that should be set to the node. If not
                specified the operator will return the value of the node
                instead.
            deep: Flag if the operation should block until the device has
                acknowledged the operation. The operation returns the value
                acknowledged by the device. This takes significantly longer
                than a normal operation and should be used carefully.
            enum: Flag if enumerated values should return the enum value as
                string or return the raw number.
            parse: Flag if the GetParser or SetParser, if present, should be
                applied or not.

        Returns:
            Value of the node for a get operation. If the deep flag is set the
            acknowledged value from the device is returned (applies also for
            the set operation).

            .. versionchanged:: 0.3.5

                Returns `WildcardResult` when wildcards are used in
                getting values.

            .. versionchanged:: 0.5.0 Returns NodeDict instead of WildcardResult

            .. versionchanged:: 0.6.1 Returns an enum on keywords nodes also
                for deep gets.

        Raises:
            AttributeError: If the connection does not support the necessary
                function to get/set the value.
            RuntimeError: If self.node_info.type if one of the following:
                [ZIPWAWave, ZITriggerSample, ZICntSample, ZIImpedanceSample,
                ZIScopeWave, ZIAuxInSample]. The reason is that these nodes can
                only be polled.
            TypeError: if the deep command is not available for this node
                (e.g. sample nodes)
            KeyError: If the node does not resolve to at least one valid leaf
                node.
        """
        if value is None:
            return self._get(deep=deep, enum=enum, parse=parse, **kwargs)
        return self._set(value, deep=deep, enum=enum, parse=parse, **kwargs)

    @lazy_property
    def _next_layer(self) -> t.Set[str]:
        """A set of direct child nodes."""
        next_layer = set()
        for node, _ in self:
            next_layer.add(node.raw_tree[len(self._tree)])
        return next_layer

    def _is_list(self) -> bool:
        """Checks if the node is a list type."""
        return len(self._next_layer) > 0 and next(iter(self._next_layer)).isdecimal()

    def _resolve_wildcards(self) -> t.List[str]:
        """Resolves potential wildcards.

        Also will resolve partial nodes to its leaf nodes.

        Returns:
            List of matched nodes in the raw path format
        """
        return resolve_wildcards_labone(
            self._root.node_to_raw_path(self), self._root.raw_dict.keys()
        )

    def _parse_get_value(
        self, value: t.Any, enum: bool = True, parse: bool = True
    ) -> t.Any:
        """Parse the raw value from the data server.

        Args:
            value: Raw value from the data server.
            enum: Flag if enumerated values should return the enum value as a
                string or as a raw number.
            parse: Flag if the GetParser, if present, should be applied or not.

        Returns:
            Parsed value
        """
        if enum and isinstance(value, (int, np.integer)):
            try:
                value = self.node_info.enum(value) if self.node_info.enum else value
            except ValueError:
                # If the value is not in the enum LabOne does weird stuff but
                # we should not raise an exception ...
                pass
        if parse:
            value = self.node_info.get_parser(value)
        return value

    def _get(
        self, deep: bool = False, enum: bool = True, parse: bool = True, **kwargs
    ) -> t.Any:
        """Get the value from the node.

        The kwargs will be forwarded to the mapped zhinst.core function call.

        Args:
            deep: Flag if the get operation should return the cached value
                from the Data Server or get the value from the device, which is
                significantly slower.
            enum: Flag if enumerated values should return the enum value as
                string or return the raw number.
            parse: Flag if the GetParser, if present, should be applied or not.

        Return:
            value(s) from the device. If multiple values matches the the node a
            dictionary of the childnodes and their value is returned. If the
            ``deep`` flag is set the value is a pair (timestamp, value) instead.

        Raises:
            AttributeError: if the connection does not support the necessary
                function the get the value.
            RuntimeError: If self.node_info.type if one of the following:
                [ZIPWAWave, ZITriggerSample, ZICntSample, ZIImpedanceSample,
                ZIScopeWave, ZIAuxInSample]. The reason is that these nodes can
                only be polled.
            TypeError: if the deep command is not available for this node
                (e.g. sample nodes) or connection object.
            KeyError: If the node does not resolve to at least one valid leaf
                node.
        """
        readable = self.node_info.readable
        if readable:
            timestamp = None
            if deep:
                timestamp, value = self._get_deep(**kwargs)
            else:
                value = self._get_cached(**kwargs)
            value = self._parse_get_value(value, enum=enum, parse=parse)
            return (timestamp, value) if deep else value
        if readable is None and (
            self.node_info.contains_wildcards or self.node_info.is_partial
        ):
            return self._get_wildcard(deep=deep, enum=enum, parse=parse, **kwargs)
        if readable is False:
            raise AttributeError(f"{self.node_info.path} is not readable.")
        raise KeyError(self.node_info.path)

    @staticmethod
    def _parse_get_entry(raw_value: t.Dict[t.Union[str, int], t.Any]):
        """Parser for the get function of zhinst.core.

        The get function in zhinst.core support multiple values and returns the
        results as a OrderdDict. This functions parses the value entry of that
        dictionary into a (timestamp, value) pair.

        Args:
            raw_value: OrderdDict from the zhinst.core get command.

        Returns:
            (timestamp, value) pair.
        """
        value = None
        timestamp = None
        try:
            value = raw_value["value"][0]
            timestamp = raw_value["timestamp"][0]
        except TypeError:
            # ZIVectorData have a different structure
            value = raw_value[0]
            if isinstance(value, dict):
                timestamp = value["timestamp"]
                value = value["vector"]
        except IndexError:
            # HF2 has not timestamp
            value = raw_value[0]
        except KeyError:
            # HF2 returns sample nodes as well but we don`t parse them
            value = raw_value
        return (timestamp, value)

    def _get_wildcard(
        self, deep=True, enum=True, parse=True, **kwargs
    ) -> t.Union[NodeDict, t.Dict[str, t.Any]]:
        """Execute a wildcard get.

        The get is performed as a deep get (for all devices except HF2)
        regardless of the ``deep`` flag. If the ``deep`` flag is not set the
        timestamp is removed to ensure concistency.

        The kwargs will be forwarded to the maped zhinst.core function call.

        Args:
            deep: Flag if the get operation should return the cached value
                from the Data Server or get the value from the device, which is
                significantly slower. The wildcard get is always performed as
                deep get but the timestamp is only returned if the ``deep```
                flag is set.
            enum: Flag if enumerated values should return the enum value as
                string or return the raw number.
            parse: Flag if the GetParser, if present, should be applied or not.

        Returns:
            ``NodeDict`` if deep is `True`. Else a dictionary.
            Dictionary or a Mapping with the values of all subnodes.

        Raises:
            KeyError: If the node does not resolve to at least one valid leaf
                node.
        """
        # modules don`t have settingsonly argument ... this will be caught in
        # a try catch block to avoid unnecessary comparisons
        kwargs.setdefault("settingsonly", False)
        kwargs.setdefault("flat", True)
        try:
            result_raw = self._root.connection.get(self.node_info.path, **kwargs)
        except TypeError:
            del kwargs["settingsonly"]
            result_raw = self._root.connection.get(self.node_info.path, **kwargs)
        if not result_raw:
            raise KeyError(self.node_info.path)
        if not kwargs["flat"]:
            return result_raw
        result = {}
        for sub_node_raw, node_value in result_raw.items():
            sub_node = self._root.raw_path_to_node(sub_node_raw)
            timestamp, value = self._parse_get_entry(node_value)
            value = sub_node._parse_get_value(value, enum=enum, parse=parse)
            # although the operation is a deep get we hide the timestamp
            # to ensure consistency
            result[sub_node_raw] = (timestamp, value) if deep else value
        return NodeDict(result)

    def _get_deep(self, **kwargs) -> t.Tuple[int, t.Any]:
        """Get the node value from the device.

        The kwargs will be forwarded to the maped zhinst.core function call.

        Note: The HF2 does not support the timestamp option and will therfore
        return None for the timestamp.

        Returns:
            (timestamp, value) from the device.

        Raises:
            TypeError: if the deep command is not available for this node
                (e.g. sample nodes)
        """
        kwargs.setdefault("settingsonly", False)
        # Flat must be set to True (if customers want the flat option they need
        # to call zhinst.core directly)
        kwargs["flat"] = True
        try:
            raw_dict = self._root.connection.get(self.node_info.path, **kwargs)
        except TypeError:
            # Modules do not support the additional flags
            raw_dict = self._root.connection.get(self.node_info.path, flat=True)
        if not raw_dict or len(raw_dict) == 0:
            raise TypeError(
                "keyword 'deep' is not available for this node. "
                "(e.g. node is a sample node)"
            )
        raw_value = next(iter(raw_dict.values()))
        return self._parse_get_entry(raw_value)

    def _get_cached(self, **kwargs) -> t.Any:
        """Get the cached node value from the data server.

        The kwargs will be forwarded to the maped zhinst.core function call.

        Returns:
            Cached node value from the data server.

        Raises:
            AttributeError: if the connection does not support the necessary
                function the get the value.
            RuntimeError: If self.node_info.type if one of the following:
                [ZIPWAWave, ZITriggerSample, ZICntSample, ZIImpedanceSample,
                ZIScopeWave, ZIAuxInSample]. The reason is that these nodes can
                only be polled.
        """
        if "Integer" in self.node_info.type:
            return self._root.connection.getInt(self.node_info.path)
        if self.node_info.type == "Double":
            return self._root.connection.getDouble(self.node_info.path)
        if self.node_info.type == "String":
            return self._root.connection.getString(self.node_info.path)
        if self.node_info.type == "ZIVectorData":
            _, value = self._get_deep(**kwargs)
            return value
        if self.node_info.type == "Complex Double":
            return self._root.connection.getComplex(self.node_info.path, **kwargs)
        if self.node_info.type == "ZIDemodSample":
            return self._root.connection.getSample(self.node_info.path, **kwargs)
        if self.node_info.type == "ZIDIOSample":
            return self._root.connection.getDIO(self.node_info.path, **kwargs)
        if self.node_info.type == "ZIAdvisorWave":
            raw_value = self._root.connection.get(self.node_info.path, flat=True)
            return next(iter(raw_value.values()))[-1]
        raise RuntimeError(
            f"{self.node_info.path} has type {self.node_info.type} and can "
            "only be polled."
        )

    def _set(
        self, value: t.Any, deep=False, enum=True, parse=True, **kwargs
    ) -> t.Optional[t.Any]:
        """Set the value to the node.

        The kwargs will be forwarded to the maped zhinst.core function call.

        Args:
            value: value
            deep: Flag if the set operation should be blocking until the data
                has arrived at the device. (default=False)
            enum: Flag if enumerated values should accept the enum value as
                string. (default=True)
            parse: Flag if the SetParser, if present, should be applied or not.
                (default=True)

        Returns:
            Acknowledged value on the device if ``deep`` flag is set (does not
            work for wildcard or non leafs nodes since they are bundled in a
            transaction).

        Raises:
            AttributeError: If the connection does not support the necessary
                function the set the value.
            KeyError: if the wildcard does not resolve to a valid node
            RuntimeError: if deep set is not possible
            TypeError: Connection does not support deep set
        """
        writable = self.node_info.writable
        if writable or self.node_info.contains_wildcards:
            if parse:
                value = self.node_info.set_parser(value)
            if self._root.transaction.in_progress():
                self._root.transaction.add(self, value)
            elif deep:
                return self._parse_get_value(
                    self._set_deep(value, **kwargs), enum=enum, parse=parse
                )
            else:
                try:
                    self._root.connection.set(self.node_info.path, value, **kwargs)
                except RuntimeError:
                    # Some vector nodes do not support support set command.
                    if self.node_info.type == "ZIVectorData":
                        self._root.connection.setVector(
                            self.node_info.path, value, **kwargs
                        )
                    else:
                        raise
            return None
        if self.node_info.is_partial:
            return self["*"](value, deep=deep, enum=enum, parse=parse, **kwargs)
        if writable is False:
            raise AttributeError(f"{self.node_info.path} is read-only.")
        raise KeyError(self.node_info.path)

    def _set_deep(self, value: t.Any, **kwargs) -> t.Any:
        """Set the node value from device.

        The kwargs will be forwarded to the mapped zhinst.core function call.

        Args:
            value: value

        Returns:
            Acknowledged value on the device. Only if a deeps set operation is
            available for the connection object.

        Raises:
            RuntimeError: if deep set is not possible
            TypeError: Connection does not support deep set
        """
        try:
            if isinstance(value, numbers.Integral):
                return self._root.connection.syncSetInt(
                    self.node_info.path, value, **kwargs
                )
            if isinstance(value, numbers.Real):
                return self._root.connection.syncSetDouble(
                    self.node_info.path, value, **kwargs
                )
            if isinstance(value, str):
                return self._root.connection.syncSetString(
                    self.node_info.path, value, **kwargs
                )
        except TypeError as error:
            raise TypeError(
                "deep set is not supported for this connection."
                "(this likely cause because the connection is a module and a deep "
                "set does not make sense there.)"
            ) from error
        raise RuntimeError(
            f"Invalid type {type(value)} for deep set "
            "(only int,float and str are supported)"
        )

    def is_child_node(self, child_node: "Node") -> bool:
        """Checks if a node is child node of this node.

        Args:
            child_node: Potential child node

        Returns:
            Boolean if passed node is a child node
        """
        return fnmatch.fnmatchcase(
            "/".join(child_node.raw_tree), "/".join(self.raw_tree) + "*"
        )

    def wait_for_state_change(
        self,
        value: t.Union[int, str, NodeEnum],
        *,
        invert: bool = False,
        timeout: float = 2,
        sleep_time: float = 0.005,
    ) -> None:
        """Waits until the node has the expected state/value.

        Warning:
            Only supports integer nodes. (The value can either be the value or
            its corresponding enum value as string)

        Args:
            value: Expected value of the node.

            .. versionchanged:: 0.6.1 Enums or strings are accepted for keywords nodes.

            invert: Instead of waiting for the value, the function will wait for
                any value except the passed value instead. (default = False)

                Useful when waiting for value to change from existing one.
            timeout: Maximum wait time in seconds. (default = 2)
            sleep_time: Sleep interval in seconds. (default = 0.005)

        Raises:
            TimeoutError: Timeout exceeded.
        """
        if self.node_info.contains_wildcards:
            start_time = time.time()
            nodes_raw = self._resolve_wildcards()
            if not nodes_raw:
                raise KeyError(self.node_info.path)
            for node_raw in nodes_raw:
                node = self._root.raw_path_to_node(node_raw)
                node.wait_for_state_change(
                    value,
                    invert=invert,
                    timeout=max(0, timeout - (time.time() - start_time)),
                    sleep_time=sleep_time,
                )
        else:
            # If the node is a keyword (has a enum defined) and the value is a string
            # converts it to the numeric value
            if self.node_info.enum and isinstance(value, str):
                enum_value = self.node_info.enum[value]
                parsed_value = self._parse_get_value(enum_value)
            else:
                parsed_value = self._parse_get_value(value)

            start_time = time.time()

            # Performs a deep get to avoid waiting on stale values from cache
            # In the loop we can use a shallow get
            # Since deep get
            curr_value = self._get(deep=True)[1]

            while start_time + timeout >= time.time():
                # Verify if we get to the correct value.
                # If yes, exit the function.
                if (curr_value == parsed_value) != invert:
                    return

                time.sleep(sleep_time)
                curr_value = self._get(deep=False)

            # In case of timeout, raise the correct error

            # If the user passed a string or enum, uses it for the error report
            if isinstance(value, (str, NodeEnum)):
                value = repr(parsed_value.name)
                curr_value = repr(curr_value.name)

            if invert:
                raise TimeoutError(
                    f"{self.node_info.path} did not change from the expected"
                    f" value {value} within {timeout}s."
                )
            raise TimeoutError(
                f"{self.node_info.path} did not change to the expected value"
                f" within {timeout}s. {value} != {curr_value}"
            )

    def subscribe(self) -> None:
        """Subscribe to this node (its child lead nodes).

        To get data from data from the subscribed nodes use the poll command
        (provided by the Connection).

        In order to avoid fetching old data that is still in the buffer execute
        a sync command before subscribing to new data streams.
        """
        try:
            self._root.connection.subscribe(self.node_info.path)
        except RuntimeError as error:
            raise KeyError(self.node_info.path) from error

    def unsubscribe(self) -> None:
        """Unsubscribe this node (its child lead nodes).

        Use this command after recording to avoid buffer overflows that may
        increase the latency of subsequent commands.
        """
        try:
            self._root.connection.unsubscribe(self.node_info.path)
        except RuntimeError as error:
            raise KeyError(self.node_info.path) from error

    def get_as_event(self) -> None:
        """Trigger an event for that node (its child lead nodes).

        The node data is returned by a subsequent poll command.
        """
        try:
            self._root.connection.getAsEvent(self.node_info.path)
        except RuntimeError as error:
            raise KeyError(self.node_info.path) from error

    def child_nodes(
        self,
        *,
        recursive: bool = False,
        leavesonly: bool = False,
        settingsonly: bool = False,
        streamingonly: bool = False,
        subscribedonly: bool = False,
        basechannelonly: bool = False,
        excludestreaming: bool = False,
        excludevectors: bool = False,
    ) -> t.Generator["Node", None, None]:
        """Generator for all child nodes that matches the filters.

        If the nodes does not contain any child nodes the generator will only
        contain the node itself (if it matches the filters).

        Warning:
            The Data Server supports only the asterisk wildcard. For all
            other wildcards the matching child nodes can be generated manually
            within the nodetree.

            Enabling additional flags how ever require that each node that
            matches the wildcard needs to be checked in a separate request by
            the Data Server which can cause a severe latency. Therefore one
            needs to enable the `full_wildcard` flag in order to support the
            manual generation of the matching child nodes.

        Examples:
            >>> child_nodes = nodetree.demods[0].child_nodes()
            >>> next(child_nodes)
            /dev1234/demods/0/freq

        Args:
            recursive: Returns the nodes recursively (default: False)
            leavesonly: Returns only nodes that are leaves, which means
                they are at the outermost level of the tree (default: False).
            settingsonly: Returns only nodes which are marked as setting
                (default: False).
            streamingonly: Returns only streaming nodes (default: False).
            subscribedonly: Returns only subscribed nodes
                (default: False).
            basechannelonly: Return only one instance of a node in case
                of multiple channels (default: False).
            excludestreaming: Exclude streaming nodes (default: False).
            excludevectors: Exclude vector nodes (default: False).

        Returns:
            Generator of all child nodes that match the filters
        """
        raw_path = self._root.node_to_raw_path(self)
        raw_result = self._root.connection.listNodes(
            raw_path,
            recursive=recursive,
            leavesonly=leavesonly,
            settingsonly=settingsonly,
            streamingonly=streamingonly,
            subscribedonly=subscribedonly,
            basechannelonly=basechannelonly,
            excludestreaming=excludestreaming,
            excludevectors=excludevectors,
        )
        for node_raw in raw_result:
            yield self._root.raw_path_to_node(node_raw)

    def is_valid(self) -> bool:
        """Check if the node is a valid node.

        Valid node means it resolves to at least one existing node in the node
        tree. Meaning not only leaf nodes are valid nodes but also partial nodes
        and nodes containing wildcards.

        Returns:
            Flag if the node is a valid node
        """
        if self._is_valid is None:
            keys = self._resolve_wildcards()
            self._is_valid = len(keys) > 0
        return self._is_valid

    def _send_set_list(self, settings: t.List[t.Tuple[str, t.Any]]) -> None:
        """Applies settings and takes care of a possibly ongoing transaction.

        In case of an active transaction, the settings will be put into it,
        rather than being applied immediately.

        Args:
            settings: List of node-string, value pairs which list the settings to
            be changed
        """
        if self.root.transaction.in_progress():
            self.root.transaction.add_raw_list(settings)
        else:
            self.root.connection.set(settings)

    @property
    def node_info(self) -> NodeInfo:
        """Additional information about the node."""
        return self.root.get_node_info(self)

    @property
    def raw_tree(self) -> t.Tuple[str, ...]:
        """Internal representation of the node."""
        return self._tree

    @property
    def root(self) -> "NodeTree":
        """Node tree to which this node belongs to."""
        return self._root


class NodeList(Sequence, Node):
    """List of nodelike objects.

    List of preinitialized classes that inherit from the ``Node`` class would not
    support wildcards since they would be of type list.

    This class holds the preinitialized objects. But if a the passed item is not
    an integer it returns a Node instead.

    Warning:
        Since in case of a passed wildcard symbol the return value is a node,
        the additional functionality that the nodelike object may provide
        (e.g. helper functions) are no longer accessible.

    Args:
        elements: Preinitialized child elements
        root: Root of the nodetree
        tree: Node tree (node path as tuple) of the current node
    """

    def __init__(self, elements: t.Sequence[t.Any], root: "NodeTree", tree: tuple):
        Sequence.__init__(self)
        Node.__init__(self, root, tree)
        self._elements: t.Sequence[t.Any] = elements

    @t.overload
    def __getitem__(
        self, idx: t.Union[int, str]
    ) -> t.Union[t.Any, Node]:  # pragma: no cover
        ...

    @t.overload
    def __getitem__(
        self, s: slice
    ) -> t.Sequence[t.Union[t.Any, Node]]:  # pragma: no cover
        ...

    def __getitem__(self, item):
        # User numpy check here to ensure numpy types are handled correctly (#252)
        if np.issubdtype(type(item), np.integer):
            return self._elements[item]
        return Node(self._root, self._tree + (str(item),))

    def __len__(self):
        return len(self._elements)

    def __eq__(self, other):
        return Node.__eq__(self, other)

    def __hash__(self):
        return Node.__hash__(self)
