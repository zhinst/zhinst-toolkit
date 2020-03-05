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

    def _getter(self):
        if "Read" in self._properties:
            value = self._device._get(self._path)
            self._cached_value = self._get_parser(value)
            return self._cached_value
        else:
            raise ZHTKNodetreeException("This parameter is not gettable!")

    def _setter(self, value):
        if "Write" in self._properties:
            if value != self._cached_value:
                value = self._set_parser(value)
                self._device._set(self._path, value)
                self._cached_value = value
            return self._cached_value
        else:
            raise ZHTKNodetreeException("This parameter is not settable!")

    def __call__(self, value=None):
        if value is None:
            return self._getter()
        else:
            return self._setter(value)

    def __repr__(self):
        s = f"Node: {self._path}\n"
        s += f"Description: {self._description}\n"
        s += f"Type: {self._type}\n"
        s += f"Properties: {self._properties}\n"
        s += f"Options: {self._options}\n"
        s += f"Unit: {self._unit}\n"
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
    the __repr__() method to make it look nice in the console.
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
        data  -- dictionary to add value to with keys
        keys  -- list of keys to traverse along tree and place value
        val   -- value for innermost layer of nested dict
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

