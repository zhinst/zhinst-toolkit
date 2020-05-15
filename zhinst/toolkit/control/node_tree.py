# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
from typing import List, Dict, Callable


class ToolkitNodeTreeError(Exception):
    pass


class Parameter:
    """Implements a :mod:`zhinst-toolkit` :class:`Parameter`.

    Implements a callable :class:`Parameter` as leaves in the :class:`NodeTree` 
    with a parent :class:`Node` and a device. It holds the information from the 
    `daq.listNodesJSON(...)` method of the Zurich Instruments Python API such as 
    the node path, the description, properties, etc. The `__repr__()` method 
    returns a string with a summary of the :class:`Parameter`.

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
            The parent object that the :class:`Parameter` is associated to.
        params (dict): Dictionary with a definition of the :class:`Parameter`. 
            It must contain the item *'Node'* corresponding to the node path of 
            the parameter on the device that is used for getting and setting the 
            :class:`Parameter` value. It may contain the items *'Description'*, 
            *'Properties'*, *'Options'*, *'Unit'*, *'Type'*. 

    Keyword Arguments:
        device (:class:`BaseInstruemnt`): The device driver that the 
            :class:`Parameter` is associated to. The device is eventually 
            used to `set(...)` and `get(...)` the node. (default: None)
        set_parser (Callable): A parser function that is called with the set 
            value before setting the value and returns the parsed parameter 
            value. (default: 'lambda v: v')
        set_parser (Callable): A parser function that is called with the gotten 
            value from the device before returning it by the getter. It returns 
            the parsed parameter value. (default: 'lambda v: v')
        mapping (dict): A value mapping for keyword to integer conversion. 
            (default: None)

    """

    def __init__(
        self,
        parent,
        params: Dict,
        device=None,
        set_parser: Callable = lambda v: v,
        get_parser: Callable = lambda v: v,
        mapping: Dict = None,
    ) -> None:
        self._parent = parent
        self._device = parent._device if device is None else device
        self._path = params["Node"]
        self._description = params.get("Description", "")
        self._type = params.get("Type", None)
        self._properties = params.get("Properties", None)
        self._options = params.get("Options", None)
        self._unit = params.get("Unit", None)
        self._cached_value = None
        self._get_parser = get_parser
        self._set_parser = set_parser
        self._map = mapping

    def _getter(self):
        """Implements a getter for the :class:`Parameter`.
        
        If 'Read' is in the parameter properties (from `listNodesJSON`), this 
        will call the '_get' method of the associated device with 'path' as 
        attribute.
        
        Raises:
            ToolkitNodeTreeError: if the parameter is not gettable, i.e. if 
                'Read' not in properties
        
        Returns:
            The  :class:`Parameter` value as returned from the `get` parser.

        """
        if "Read" in self._properties:
            value = self._device._get(self._path)
            if self._map is not None:
                if value not in self._map.keys():
                    raise ToolkitNodeTreeError(
                        f"The value '{value}' is not in {list(self._map.keys())}."
                    )
                value = self._map[value]
            self._cached_value = self._get_parser(value)
            return self._cached_value
        else:
            raise ToolkitNodeTreeError("This parameter is not gettable!")

    def _setter(self, value):
        """Implements a setter for the :class:`Parameter`. 
        
        If 'Write' is in the  :class:`Parameter` properties (from 
        `listNodesJSON`), this will call the '_set' method of the associated 
        device with 'path' and 'value' as attributes.
        
        Arguments:
            value: value to be set
        
        Raises:
            ToolkitNodeTreeError: if the  :class:`Parameter` is not settable, 
                i.e. if 'Write' not in properties
        
        Returns:
            The  :class:`Parameter` value set on the device.

        """
        if "Write" in self._properties:
            if value != self._cached_value:
                if self._map is not None and isinstance(value, str):
                    if value not in self._map.values():
                        raise ToolkitNodeTreeError(
                            f"The value '{value}' is not in {list(self._map.values())}."
                        )
                    inv_map = {v: k for k, v in self._map.items()}
                    value = inv_map[value]
                value = self._set_parser(value)
                self._device._set(self._path, value)
                self._cached_value = self._get_parser(value)
            return self._cached_value
        else:
            raise ToolkitNodeTreeError("This parameter is not settable!")

    def __call__(self, value=None):
        """Make the object callable.

        Override the `__call__(...)` method for setting and getting the 
        :class:`Parameter` value. The  :class:`Parameter` can then be gotten by 
        calling it with no arguments. It is set by calling it with the value as 
        an argument. This works similarly to parameters in :mod:`qcodes`.
        
        Arguments:
            value:  An optional value to call the  :class:`Parameter` with if it 
                is `set`, leaving the argument out `gets` the  :class:`Parameter` 
                from the device. (default: None)

        Returns:
            The value that has been set if a value is specified, otherwise the 
            returned value from the `getter`.
        
        """
        if value is None:
            return self._getter()
        else:
            return self._setter(value)

    def __repr__(self):
        s = f"Node: {self._path}\n"
        if self._description is not None:
            s += f"Description: {self._description}\n"
        if self._type is not None:
            s += f"Type: {self._type}\n"
        if self._properties is not None:
            s += f"Properties: {self._properties}\n"
        if self._options is not None:
            s += f"Options: {self._options}\n"
        if self._map is not None:
            s += f"Mapping: {self._map}\n"
        if self._unit is not None:
            s += f"Unit: {self._unit}\n"
        if self._cached_value is not None:
            s += f"Value: {self._cached_value}\n"
        return s


class Node:
    """Implements a node in the :class:`NodeTree` of a device. 
    
    A :class:`Node` has a parent node and a device it is associated with. It can 
    hold other :class:`Nodes` as well as :class:`Parameters`. The data structure 
    of the device :class:`NodeTree` is recreated by recursively adding either 
    other :class:`Nodes` or :class:`Parameters` as attributes to the 
    :class:`Node`.

    To make it easier fo the user to navigate the device :class:`NodeTree`, each
    :class:`Node` has the attributes `nodes` and `parameters` taht holds a list 
    its children. Also the `__repr__()` method is overwritten such that the 
    output in the console is useful:  

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


    Attributes:
        nodes (list): A list of other :class:`Node` s that are children of this 
            :class:`Node`.
        parameters (list): A list of :class:`Parameters` that are children of 
            this :class:`Node`.

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
        """Recursively adds class:`Nodes` and/or :class:`Parameters` to a parent 
        :class:`Node`.

        Recursively goes through a nested nodetree dictionary. Adds a 
        :class:`Node` object as attribute to the parent node if the leave of the 
        :class:`NodeTree` has not yet been reached. Adds a :class:`Parameter` as 
        attribute to the parent node if the leave has been reached (i.e. when 
        'Node' is in keys of the remaining dict and the remaining dict is the s
        ame as the one return from `listNodesJSON` describing the 
        :class:`Parameter`).

        If a layer in the :class:`NodeTree` is enumerated and the keys of the 
        dict are integer values (e.g. 'sigouts/0/..', 'sigouts/1/..', 
        'sigouts/2/..', ...) a :class:`NodeList` is created instead. In case the 
        :class:`NodeList` has only one entry (e.g. for 'qas/0/..') only a single 
        :class:`Node` is added and the plural of 'qas' is turned into 'qa'.
        
        Arguments:
            parent (:class:`Node`): The parent :class:`Node` that the 
                :class:`Nodes` or :class:`Parameters` are added to as attributes.
            nodetree_dict (dict): A (sub-)dictionary containing the next 
                :class:`Nodes` and/or :class:`Parameters` as dicts. 

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
    
    Simply inherits from :class:`List` and overrides the `__repr__()` method to 
    make it look nice in the console or in a notebook.

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

    Implements a :class:`NodeTree` data structure used to access the settings 
    (:class:`Parameter`) of any Zurich Instruments device. A :class:`NodeTree` 
    is created for every instrument when it is connected to the data server. In 
    this way the available settings always directly correspond to the 
    :class:`Nodes` that are available on the device.

    Inherits from the :class:`Node` class. On initialization the 
    :class:`NodeTree` retireves a nested dictionary from the device representing 
    its nodetree heirarchy and then recursively adds :class:`Nodes` and 
    :class:`Parameters` as attributes to the :class:`Node`.

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
        device (:class:`BaseInstrument`): A reference to the instrument that 
            the :class:`NodeTree` belongs to. Used for `getting` and `setting` 
            of each :class:`Parameter`.
    
    Attributes:
        device (:class:`BaseInstrument`): The associated device.
        nodetree_dict (dict): A nested dictionary created from the dict 
            returned by `daq.listNodesJSON(...)` of the :mod:`zhinst.ziPython` 
            Python API. 

    """

    def __init__(self, device) -> None:
        self._device = device
        self._nodetree_dict = self._get_nodetree_dict()
        self._init_subnodes_recursively(self, self._nodetree_dict)

    def _get_nodetree_dict(self) -> Dict:
        """Gets the :class:`NodeTree` as a nested dictionary. 

        Retrieves the :class:`NodeTree` from the device as a flat dictionary and 
        converts it to a nested dictionary using `dictify()`. For every device 
        node returned from the instrument this method splits the node string 
        into its parts and sorts the value (dict with 'Node', 'Description', 
        'Unit', etc.) into a nested dict that recreates the hierarchy of the 
        :class:`NodeTree`.

        """
        tree = self._device._get_nodetree(f"{self._device.serial}/*")
        nodetree = {}
        for key, value in tree.items():
            key = key.replace(f"/{self._device.serial.upper()}/", "")
            hierarchy = key.split("/")
            dictify(nodetree, hierarchy, value)
        return nodetree


def dictify(data, keys: List, val: Dict) -> Dict:
    """Turns a flat :class:`NodeTree` dictionary into a nested dictionary.

    Helper function to generate nested dictionary from list of keys and value. 
    Calls itself recursively.
    
    Arguments:
        data (dict): A dictionary to add value to with keys.
        keys (list): A list of keys to traverse along tree and place value.
        val (dict): A value for innermost layer of nested dict.

    """
    key = keys[0]
    key = int(key) if key.isdecimal() else key.lower()
    if len(keys) == 1:
        data[key] = val
    else:
        if key in data.keys():
            data[key] = dictify(data[key], keys[1:], val)
        else:
            data[key] = dictify({}, keys[1:], val)
    return data
