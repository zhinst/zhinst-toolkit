# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np


class ZHTKNodetreeException(Exception):
    pass


class Parameter:
    """
    Implements a callable parameter as leaves in the nodetree with a parent node 
    and a device. It holds the information from the daq.listNodesJSON(...) 
    method such as the node path, the description, properties, etc. The 'help' 
    property prints a string with a summary of the parameter.

    """

    def __init__(
        self,
        parent,
        params,
        device=None,
        set_parser=lambda v: v,
        get_parser=lambda v: v,
        mapping: dict = None,
    ):
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
        """
        Implements a getter for the parameter, if 'Read' is in the parameter 
        properties (from listNodesJSON), this will call the '_get' method of the 
        associated device with 'path' as attribute.
        
        Raises:
            ZHTKNodetreeException: if the parameter is not gettable, i.e. if 
                'Read' not in properties
        
        Returns:
            the gotten value

        """
        if "Read" in self._properties:
            value = self._device._get(self._path)
            if self._map is not None:
                if value not in self._map.keys():
                    raise ZHTKNodetreeException(
                        f"The value '{value}' is not in {list(self._map.keys())}."
                    )
                value = self._map[value]
            self._cached_value = self._get_parser(value)
            return self._cached_value
        else:
            raise ZHTKNodetreeException("This parameter is not gettable!")

    def _setter(self, value):
        """
        Implements a setter for the parameter, if 'Write' is in the parameter 
        properties (from listNodesJSON), this will call the '_set' method of the 
        associated device with 'path' and 'value' as attributes.
        
        Arguments:
            value: value to be set
        
        Raises:
            ZHTKNodetreeException: if the parameter is not settable, i.e. if 
                'Write' not in properties
        
        Returns:
            the set value

        """
        if "Write" in self._properties:
            if value != self._cached_value:
                if self._map is not None and isinstance(value, str):
                    value = value.lower()
                    if value not in self._map.values():
                        raise ZHTKNodetreeException(
                            f"The value '{value}' is not in {list(self._map.values())}."
                        )
                    inv_map = {v: k for k, v in self._map.items()}
                    value = inv_map[value]
                value = self._set_parser(value)
                self._device._set(self._path, value)
                self._cached_value = value
            return self._cached_value
        else:
            raise ZHTKNodetreeException("This parameter is not settable!")

    def __call__(self, value=None):
        """
        Override the __call__ method for setting and getting the Parameter 
        value. The Parameter can then be gotten by calling it with no arguments. 
        It is set by calling it with the value as an argument. This works
        similarly to parameters in QCoDeS.
        
        Arguments:
            value:  optional value to call the parameter with if it is set, 
                leaving the argumetn out gets the parameter(default: None)

        Returns:
            either the set or gotten value
        
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
    """
    Implements a node in the nodetree of a device. A node has a parent node 
    and a device it is associated with. It can hold other nodes as well as 
    parameters. The data structure of the device nodetree is recreated by 
    recursively adding either nodes or parameters as attributes to the node.

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
        """
        Recursively goes through a nested nodetree dictionary. Adds a Node 
        object as attribute to the parent node if the leave of the nodetree has 
        not yet been reached. Adds a Parameter as attribute to the parent node
        if the leave has been reached (i.e. when 'Node' is in keys of the 
        remaining dict and the remaining dict is the same as the one return 
        from listNodesJSON describing the parameter).

        If a layer in the nodetree is enumerated and the keys of the dict are 
        integer values (e.g. 'sigouts/0/..', 'sigouts/1/..', 'sigouts/2/..', ...) 
        a NodeList is created instead. In case the NodeList has only one entry 
        (e.g. for 'qas/0/..') only a single node is added and the plural of 
        'qas' is turned into 'qa'.
        
        Arguments:
            parent (Node): parent node that the Nodes or Parameters are added 
                to as attributes
            nodetree_dict (dict): (sub-)dictionary containing the next Nodes 
                and/or Parameters as dicts 

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
    """
    Implements a list of nodes. Simply inherits from List and overrides 
    the __repr__() method to make it look nice in the console or in a notebook.

    """

    def __repr__(self):
        s = f"Iterable node with {len(self)} items: \n"
        for i in range(len(self)):
            s += f"\nNode {i+1}:\n"
            s += f"{self.__getitem__(i)}\n"
        return s


class Nodetree(Node):
    """
    Implements a Nodetree data structure used to access the settings (nodes) 
    of any ZI device. A nodetree is created for every instrument when it is 
    connected to the data server. In this way the available settings always 
    directly correspond to the ndoes that are available on the device.

    Inherits from the Node class. On initialization the nodetree gets a nested 
    dictionary representing the nodetree hirarchy and then recursively adds 
    Node and Parameter objects as attributes to the node.
    
    Args:
        device: reference to the instrument the nodetree 
            belong to. Used for getting and setting of each parameter.
    
    Attributes:
        device (BaseInstrument)
        nodetree_dict (dict): a nested dictionary created from the dict 
            returned by daq.listNodesJSON(...) in zhinst.ziPython. 

    """

    def __init__(self, device):
        self._device = device
        self._nodetree_dict = self._get_nodetree_dict()
        self._init_subnodes_recursively(self, self._nodetree_dict)

    def _get_nodetree_dict(self):
        """
        Retrieves the nodetree from the device as a flat dictionary and 
        converts it to a nested dictionary using dictify(). For every device 
        node returned from the instrument this method splits the node string 
        into its parts and sorts the value (dict with node, description, unit, 
        etc.) into a nested dict that recreates the hirarchy of the nodetree.

        """
        tree = self._device._get_nodetree(f"{self._device.serial}/*")
        nodetree = {}
        for key, value in tree.items():
            key = key.replace(f"/{self._device.serial.upper()}/", "")
            hirarchy = key.split("/")
            dictify(nodetree, hirarchy, value)
        return nodetree


def dictify(data, keys, val):
    """
    Helper function to generate nested dictionary from list of keys and value. 
    Calls itself recursively.
    
    Arguments:
        data (dict): dictionary to add value to with keys
        keys (list): list of keys to traverse along tree and place value
        val (dict): value for innermost layer of nested dict

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

