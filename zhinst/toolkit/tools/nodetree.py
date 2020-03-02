import numpy as np


class ZIParameter:
    def __init__(self, parent, params):
        self._parent = parent
        self._device = parent._device
        self._path = params["Node"]
        self._description = params.get("Description", "")
        self._type = params.get("Type", None)
        self._properties = params.get("Properties", None)
        self._unit = params.get("Unit", None)
        self._cached_value = None

    def get(self):
        if "Read" in self._properties:
            self._cached_value = self._device.get(self._path)
            return self._cached_value
        else:
            raise Exception("This parameter is not gettable!")

    def set(self, value):
        if "Write" in self._properties:
            if value != self._cached_value:
                self._device.set(self._path, value)
                self._cached_value = value
            return self._cached_value
        else:
            raise Exception("This parameter is not settable!")


class ZINode:
    def __init__(self, parent):
        self._parent = parent
        self._device = parent._device

    @property
    def nodes(self):
        return [k for k, v in self.__dict__.items() if isinstance(v, (ZINode, list))]

    @property
    def parameters(self):
        return [k for k, v in self.__dict__.items() if isinstance(v, ZIParameter)]

    def _init_subnodes_recursively(self, parent, nodetree_dict: dict):
        for key, value in nodetree_dict.items():
            if all(isinstance(k, int) for k in value.keys()):
                if "Node" in value[0].keys():
                    for k in value.keys():
                        param = ZIParameter(parent, value[k])
                        setattr(parent, f"{key}{k}", param)
                else:
                    channel_list = []
                    for k in value.keys():
                        ch = ZINode(parent)
                        channel_list.append(ch)
                        self._init_subnodes_recursively(ch, value[k])
                    setattr(parent, key, channel_list)
            else:
                if "Node" in value.keys():
                    param = ZIParameter(parent, value)
                    setattr(parent, key, param)
                else:
                    node = ZINode(parent)
                    setattr(parent, key, node)
                    self._init_subnodes_recursively(node, value)


class ZINodetree(ZINode):
    def __init__(self, device):
        self._device = device
        self._nodetree_dict = self._get_nodetree_dict()
        self._init_subnodes_recursively(self, self._nodetree_dict)

    def _get_nodetree_dict(self):
        tree = self._device.get_nodetree("*")
        nodetree = dict()
        for key, value in tree.items():
            key = key.replace(f"/{self._device.serial.upper()}/", "")
            hirarchy = key.split("/")
            dictify(nodetree, hirarchy, value)
        return nodetree


"""
Helper functions used to process the nodetree dictionary in ZIBaseInstrument.
"""


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


def dict_to_doc(d):
    """
    Turn dictionary into pretty doc string.
    """
    s = ""
    for k, v in d.items():
        s += f"* {k}:\n\t{v}\n\n"
    return s
