# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""Zurich Instruments Toolkit (zhinst-toolkit) Nodes and Parameters.

This module implements the Nodetree, Node, Node List and Parameter
classes necessary for representing the nodetree structure and accessing
the settings of any Zurich Instruments device.
"""

import re
from typing import List, Dict, Callable, Union, Any
import keyword

from zhinst.toolkit.interface import LoggerModule

_logger = LoggerModule(__name__)


class Parameter:
    """Implements a :mod:`zhinst-toolkit` :class:`Parameter`.

    Implements a callable :class:`Parameter` as leaves in the
    :class:`NodeTree` with a parent :class:`Node` and a device. It
    holds the information from the `daq.listNodesJSON(...)` method of
    the Zurich Instruments Python API such as the node path, the
    description, properties, etc. The `__repr__()` method returns a
    string with a summary of the :class:`Parameter`.

        >>> uhfqa.nodetree.osc.freq
        Node: /DEV2266/OSCS/0/FREQ
        Description: Frequency control of the oscillator.
        Type: Double
        Properties: Read, Write, Setting
        Options: none
        Unit: Hz
        Value: none

    Setting and getting a :class:`Parameter` is easy. Just call the
    :class:`Parameter` with or without an argument:

        >>> uhfqa.nodetree.osc.freq(10e6)
        >>> uhfqa.nodetree.osc.freq()
        10000000.00

    Arguments:
        parent (:class:`BaseInstrument`, :class:`NodeTree` or :class:`Node`):
            The parent object that the :class:`Parameter` is associated
            to.
        params (dict): Dictionary with a definition of the
            :class:`Parameter`. It must contain the item *'Node'*
            corresponding to the node path of the parameter on the
            device that is used for getting and setting the
            :class:`Parameter` value. It may contain the items
            *'Description'*, *'Properties'*, *'Options'*, *'Unit'*,
            *'Type'*.
        device (:class:`BaseInstruemnt`): The device driver that the
            :class:`Parameter` is associated to. The device is
            eventually used to `set(...)` and `get(...)` the node
            (default: None).
        set_parser (Callable or list): A parser function or a list of
            parser functions that are called with the set value before
            setting the value and return the parsed parameter value
            (default: 'lambda v: v').
        get_parser (Callable): A parser function that is called with
            the gotten value from the device before returning it by the
            getter. It returns the parsed parameter value
            (default: 'lambda v: v').
        auto_mapping (bool): A flag that specifies whether a value
            mapping should be constructed automatically from the
            options obtained from the device node.
        mapping (dict): A value mapping for keyword to integer
            conversion (default: None).

    """

    def __init__(
        self,
        parent,
        params: Dict,
        device=None,
        set_parser: Union[Callable, list] = lambda v: v,
        get_parser: Callable = lambda v: v,
        auto_mapping: bool = False,
        mapping: Dict = None,
        dynamic_path: Callable = None,
    ) -> None:
        self._parent = parent
        self._device = parent._device if device is None else device
        self._path = params["Node"]
        self._description = params.get("Description", "")
        self._type = params.get("Type", None)
        self._properties = params.get("Properties", None)
        self._options = params.get("Options", None)
        self._unit = params.get("Unit", None)
        self._get_parser = get_parser
        self._set_parser = set_parser
        self._auto_mapping = auto_mapping
        self._map = mapping
        self._map_extended = None
        self._inverse_map = {}
        self._flat_mapping_values = []
        if self._map is None and self._auto_mapping is True:
            # Construct automatic mapping from options if no manual
            # mapping is specified and automatic mapping is activated.
            self._construct_auto_mapping()
            # Do not display the automatic mapping in the docstring
            # since it is basically the same as options.
            self._display_mapping = False
        else:
            # Otherwise, display the automatic mapping in the docstring
            self._display_mapping = True
        if dynamic_path is None:
            self._dynamic_path = lambda v: self._path
        else:
            self._dynamic_path = dynamic_path

    def _getter(self):
        """Implements a getter for the :class:`Parameter`.

        If 'Read' is in the parameter properties (from `listNodesJSON`),
        this will call the '_get' method of the associated device with
        'path' as attribute.

        Raises:
            ToolkitNodeTreeError: if the parameter is not gettable,
                i.e. if 'Read' not in properties
            ValueError: if the  :class:`Parameter` has a value mapping
                and the gotten value is not among the allowed values

        Returns:
            The  :class:`Parameter` value as returned from the `get`
            parser.

        """
        if "Read" in self._properties:
            path = self._dynamic_path(self._parent)
            value = self._device._get(path)
            if self._map is not None:
                allowed_values = list(self._map.keys())
                if value not in allowed_values:
                    _logger.error(
                        f"The value '{value}' is not in {allowed_values}.",
                        _logger.ExceptionTypes.ValueError,
                    )
                value = self._map[value]
                # If the mapping has more than one value assigned to the
                # same key, choose the first one in the list.
                if isinstance(value, list):
                    value = value[0]
            return self._get_parser(value)
        else:
            _logger.error(
                "This parameter is not gettable!",
                _logger.ExceptionTypes.ToolkitNodeTreeError,
            )

    def _setter(self, value, sync=False):
        """Implements a setter for the :class:`Parameter`.

        If 'Write' is in the  :class:`Parameter` properties (from
        `listNodesJSON`), this will call the '_set' method of the
        associated device with 'path' and 'value' as attributes.

        Arguments:
            value: value to be set

        Keyword Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after setting the :class:`Parameter` value
                (default: False).

        Raises:
            ToolkitNodeTreeError: if the  :class:`Parameter` is not
                settable, i.e. if 'Write' not in properties
            ValueError: if the  :class:`Parameter` has a value mapping
                and the input value is not among the allowed values

        Returns:
            The  :class:`Parameter` value set on the device.

        """
        if "Write" in self._properties:
            if self._map is not None and isinstance(value, str):
                # Construct a list from all allowed values in the mapping
                allowed_values = self._flatten_mapping_values()
                if value not in allowed_values:
                    _logger.error(
                        f"The value '{value}' is not in {allowed_values}.",
                        _logger.ExceptionTypes.ValueError,
                    )
                inverse_map = self._invert_mapping()
                value = inverse_map[value]
            elif self._map is not None and isinstance(value, int):
                allowed_values = list(self._map.keys())
                if value not in allowed_values:
                    _logger.error(
                        f"The value '{value}' is not in {allowed_values}.",
                        _logger.ExceptionTypes.ValueError,
                    )
            # If the set_parser is a list of callables, call them
            # one by one inside a loop
            if isinstance(self._set_parser, list):
                for callable_element in self._set_parser:
                    value = callable_element(value)
            else:
                value = self._set_parser(value)
            path = self._dynamic_path(self._parent)
            if self._type == "ZIVectorData":
                self._device._set_vector(path, value)
            else:       
                self._device._set(path, value, sync=sync)
        else:
            _logger.error(
                "This parameter is not settable!",
                _logger.ExceptionTypes.ToolkitNodeTreeError,
            )

    def _invert_mapping(self):
        """Invert the map dictionary to create inverse mapping."""
        if self._inverse_map == {}:
            for key, value in self._map.items():
                if isinstance(value, list):
                    self._inverse_map.update(dict.fromkeys(value, key))
                else:
                    self._inverse_map.update(dict({value: key}))
        return self._inverse_map

    def _flatten_mapping_values(self):
        """Combine all dictionary values in a single list."""
        if not self._flat_mapping_values:
            nested_list = self._map.values()
            for sublist in nested_list:
                if isinstance(sublist, list):
                    for value in sublist:
                        self._flat_mapping_values.append(value)
                else:
                    value = sublist
                    self._flat_mapping_values.append(value)
        return self._flat_mapping_values

    @staticmethod
    def _reformat_options_dict(options):
        """Insert a new line character after each option

        This method allows the options to be displayed in a more human
        readable way
        """
        return re.sub(r" '\d+':", "\\n\\g<0>", str(options))

    def _construct_auto_mapping(self):
        """Generate a automatic mapping from the options

        The options are extracted from the node of the device. If no
        mapping is provided manually and `auto_mapping` is set to True
        a mapping will be automatically constructed from the options.
        The key values are converted from str to int."""
        if self._options is None:
            _logger.error(
                "Automatic mapping cannot be constructed. This node does not "
                "contain any information regarding the allowed options!",
                _logger.ExceptionTypes.ToolkitNodeTreeError,
            )

        elif self._options is not None:
            map_from_options = {}
            map_from_options_extended = {}
            options = self._options
            for key, value in options.items():
                value_split = value.split(": ")
                value_options = value_split[0].split(", ")
                value_options = [re.sub(r'"', "", option) for option in value_options]
                value_options_extended = value_options.copy()
                if len(value_split) > 1:
                    value_options_extended.append(value_split[1].strip("."))
                if len(value_options) < 2:
                    value_options = value_options[0]
                map_from_options.update(dict({int(key): value_options}))
                map_from_options_extended.update(
                    dict({int(key): value_options_extended})
                )
            self._map = dict(map_from_options)
            self._map_extended = dict(map_from_options_extended)

    def assert_value(
        self,
        value: Any,
        blocking: bool = True,
        timeout: float = 2,
        sleep_time: float = 0.005,
    ) -> None:
        """Check if the parameter has the expected value.

        Passes the keyword arguments to the `_assert_node_value` of the
        :class:`BaseInstrument`.

        Arguments:
            value (Any): Value the parameter is expected to change to.
            blocking (bool): A flag that specifies if the program should
                be blocked until the node has the expected value
                (default: True).
            timeout (float): Maximum time in seconds the program waits
                when `blocking` is set to `True` (default: 2).
            sleep_time (float): Time in seconds to wait between
                requesting the node value (default: 0.005)

        Raises:
            ToolkitConnectionError: If called and the device in not yet
                connected to the data server.

        Returns:
            Either `True` or `False` to indicate whether the node does
            or does not have the expected value

        """
        # Process the value if it is a string
        # and extract the integer from the mapping
        if self._map is not None and isinstance(value, str):
            inverse_map = self._invert_mapping()
            value = inverse_map[value]
        # If the set_parser is a list of callables, call them
        # one by one inside a loop
        if isinstance(self._set_parser, list):
            for callable_element in self._set_parser:
                value = callable_element(value)
        else:
            value = self._set_parser(value)
        path = self._dynamic_path(self._parent)
        return self._device._assert_node_value(
            path, value, blocking=blocking, timeout=timeout, sleep_time=sleep_time
        )

    def __call__(self, value=None, sync=False):
        """Make the object callable.

        Override the `__call__(...)` method for setting and getting the
        :class:`Parameter` value. The  :class:`Parameter` can then be
        gotten by calling it with no arguments. It is set by calling it
        with the value as an argument. This works similarly to
        parameters in :mod:`qcodes`.

        Keyword Arguments:
            value:  An optional value to call the  :class:`Parameter`
                with if it is `set`, leaving the argument out `gets`
                the :class:`Parameter` from the device (default: None).
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after setting the :class:`Parameter` value
                (default: False).

        Returns:
            The value that the setter returns if a value is specified,
            otherwise the returned value from the `getter`.

        """
        if value is None:
            return self._getter()
        else:
            return self._setter(value, sync)

    def __repr__(self):
        s = f"Node: {self._dynamic_path(self._parent)}\n"
        if self._description is not None:
            s += f"Description: {self._description}\n"
        if self._type is not None:
            s += f"Type: {self._type}\n"
        if self._properties is not None:
            s += f"Properties: {self._properties}\n"
        if self._options is not None:
            options_reformatted = self._reformat_options_dict(self._options)
            s += f"Options: {options_reformatted}\n"
        if self._map is not None and self._display_mapping:
            s += f"Mapping: {self._map}\n"
        if self._unit is not None:
            s += f"Unit: {self._unit}\n"
        return s


class Node:
    """Implements a node in the :class:`NodeTree` of a device.

    A :class:`Node` has a parent node and a device it is associated
    with. It can hold other :class:`Nodes` as well as
    :class:`Parameters`. The data structure of the device
    :class:`NodeTree` is recreated by recursively adding either other
    :class:`Nodes` or :class:`Parameters` as attributes to the
    :class:`Node`.

    To make it easier fo the user to navigate the device
    :class:`NodeTree`, each :class:`Node` has the attributes `nodes`
    and `parameters` that holds a list its children. Also the
    `__repr__()` method is overwritten such that the output in the
    console is useful:

        >>> hdawg.nodetree.sigouts[0]
        <zhinst.toolkit.tools.nodetree.Node object at 0x0000021E49397470>
        nodes:
        - precompensation
        parameters:
        - on
        - range
        - direct
        - over
        ...

    Arguments:
        parent (:class:`Node`): The parent :class:`Node` that the
            :class:`Nodes` or :class:`Parameters` are added to as
            attributes.

    Attributes:
        nodes (list): A list of other :class:`Node` s that are children
            of this :class:`Node`.
        parameters (list): A list of :class:`Parameter` s that are
            children of this :class:`Node`.

    """

    def __init__(self, parent):
        self._parent = parent
        self._device = parent._device

    @property
    def nodes(self):
        return [k for k, v in self.__dict__.items() if isinstance(v, (Node, list))]

    @property
    def parameters(self):
        return [k for k, v in self.__dict__.items() if isinstance(v, Parameter)]

    def _init_subnodes_recursively(self, parent, nodetree_dict: dict):
        """Recursively adds class:`Nodes` and/or :class:`Parameters`
        to a parent :class:`Node`.

        Recursively goes through a nested nodetree dictionary. Adds a
        :class:`Node` object as attribute to the parent node if the
        leave of the :class:`NodeTree` has not yet been reached. Adds a
        :class:`Parameter` as attribute to the parent node if the leave
        has been reached (i.e. when 'Node' is in keys of the remaining
        dict and the remaining dict is the same as the one return from
        `listNodesJSON` describing the :class:`Parameter`).

        If a layer in the :class:`NodeTree` is enumerated and the keys
        of the dict are integer values (e.g. 'sigouts/0/..',
        'sigouts/1/..', 'sigouts/2/..', ...) a :class:`NodeList` is
        created instead. In case the :class:`NodeList` has only one
        entry (e.g. for 'qas/0/..') only a single :class:`Node` is
        added and the plural of 'qas' is turned into 'qa'.

        Arguments:
            parent (:class:`Node`): The parent :class:`Node` that the
                :class:`Nodes` or :class:`Parameters` are added to as
                attributes.
            nodetree_dict (dict): A (sub-)dictionary containing the
                next :class:`Nodes` and/or :class:`Parameters` as
                dicts.

        """
        for key, value in nodetree_dict.items():
            if all(isinstance(k, int) for k in value.keys()):
                lst = NodeList()
                for k in value.keys():
                    if "Node" in value[k].keys():
                        param = Parameter(parent, value[k])
                        lst.append(param)
                    else:
                        node = Node(parent)
                        lst.append(node)
                        self._init_subnodes_recursively(node, value[k])
                if len(lst) == 1:
                    key = key[:-1]
                    setattr(parent, key, lst[0])
                else:
                    setattr(parent, key, lst)
            else:
                if "Node" in value.keys():
                    param = Parameter(parent, value)
                    setattr(parent, key, param)
                else:
                    node = Node(parent)
                    setattr(parent, key, node)
                    self._init_subnodes_recursively(node, value)

    def __repr__(self):
        s = super().__repr__()
        s += f"\n"
        s += f"nodes:\n"
        for n in self.nodes:
            if n != "_parent":
                s += f" - {n}\n"
        s += f"parameters:\n"
        for p in self.parameters:
            s += f" - {p}\n"
        return s


class NodeList(list):
    """Implements a list of :class:`Nodes`.

    Simply inherits from :class:`List` and overrides the `__repr__()`
    method to make it look nice in the console or in a notebook.

        >>> hdawg.nodetree.sigouts
        Iterable node with 8 items:
            Node 1:
            <zhinst.toolkit.tools.nodetree.Node object at 0x0000021E49397470>
            nodes:
            - precompensation
            parameters:
            - on
            - range
            - direct
            - over
        ...
        >>> for sigout in hdawg.nodetree.sigouts:
        >>>     sigout.range(1.5)

    """

    def __repr__(self):
        s = f"Iterable node with {len(self)} items: \n"
        for i in range(len(self)):
            s += f"\nNode {i+1}:\n"
            s += f"{self.__getitem__(i)}\n"
        return s


class NodeTree(Node):
    """Recreates the device's nodetree.

    Implements a :class:`NodeTree` data structure used to access the
    settings (:class:`Parameter`) of any Zurich Instruments device.
    A :class:`NodeTree` is created for every instrument when it is
    connected to the data server. In this way the available settings
    always directly correspond to the :class:`Nodes` that are available
    on the device.

    Inherits from the :class:`Node` class. On initialization the
    :class:`NodeTree` retireves a nested dictionary from the device
    representing its nodetree heirarchy and then recursively adds
    :class:`Nodes` and :class:`Parameters` as attributes to the
    :class:`Node`.

    An underscore will be appended to nodes that are identical to
    reserved keywords in Python (e.g., `in` -> `in_`).

        >>> hdawg.nodetree
        <zhinst.toolkit.tools.nodetree.NodeTree object at 0x0000021E467D3BA8>
        nodes:
        - stats
        - oscs
        - status
        - sines
        - awgs
        - dio
        - system
        - sigouts
        - triggers
        - features
        - cnts
        parameters:
        - clockbase

    Arguments:
        device (:class:`BaseInstrument`): A reference to the instrument
            that the :class:`NodeTree` belongs to. Used for `getting`
            and `setting` of each :class:`Parameter`.

    Attributes:
        device (:class:`BaseInstrument`): The associated device.
        nodetree_dict (dict): A nested dictionary created from the dict
            returned by `daq.listNodesJSON(...)` of the
            :mod:`zhinst.ziPython` Python API.

    """

    def __init__(self, device) -> None:
        self._device = device
        self._nodetree_dict = self._get_nodetree_dict()
        self._init_subnodes_recursively(self, self._nodetree_dict)

    def _get_nodetree_dict(self) -> Dict:
        """Gets the :class:`NodeTree` as a nested dictionary.

        Retrieves the :class:`NodeTree` from the device as a flat
        dictionary and converts it to a nested dictionary using
        `dictify()`. For every device node returned from the instrument
        this method splits the node string into its parts and sorts the
        value (dict with 'Node', 'Description', 'Unit', etc.) into a
        nested dict that recreates the hierarchy of the
        :class:`NodeTree`.

        """
        # remove device id form key (case insensitive).
        device_id_regex = re.compile(
            re.escape(f"/{self._device.serial.upper()}/"), re.IGNORECASE
        )
        tree = self._device._get_nodetree(f"{self._device.serial}/*")
        nodetree = {}
        for key, value in tree.items():
            key = device_id_regex.sub("", key)
            hierarchy = key.split("/")
            dictify(nodetree, hierarchy, value)
        return nodetree


def dictify(data, keys: List, val: Dict) -> Dict:
    """Turns a flat :class:`NodeTree` dictionary into a nested
    dictionary.

    Helper function to generate nested dictionary from list of keys and
    value. Calls itself recursively.

    An underscore will be appended to keys that are identical to
    reserved keywords in Python (e.g., `in` -> `in_`).

    Arguments:
        data (dict): A dictionary to add value to with keys.
        keys (list): A list of keys to traverse along tree and place
            value.
        val (dict): A value for innermost layer of nested dict.

    """
    key = keys[0]
    if key.isdecimal():
        key = int(key)
    else:
        key = key.lower()
        key += "_" if keyword.iskeyword(key) else ""
    if len(keys) == 1:
        data[key] = val
    else:
        if key in data.keys():
            data[key] = dictify(data[key], keys[1:], val)
        else:
            data[key] = dictify({}, keys[1:], val)
    return data
