import zhinst
import zhinst.utils

import time
import numpy as np
import textwrap


class HDAWG(object):

    #################################################################
    def connect(self, address, port=8004, api_level=6):
        """open connection to HDAWG device, initialize DAQ object
        
        Arguments:
            object {self} -- self
            address {string} -- device address, e.g. "dev8030" or "dev8030-1" for indexing
        
        Keyword Arguments:
            port {int} -- default port to discover device (default: {8004})
            api_level {int} -- ziPython API level (default: {6})
        """
        if address == "":
            self.daq = zhinst.utils.autoConnect(default_port=port, api_level=api_level)
            self.device = zhinst.utils.autoDetect(self.daq)
        else:
            address = address.replace("-1", "")
            address = address.replace("-2", "")
            (self.daq, self.device, _) = zhinst.utils.create_api_session(
                address,
                api_level,
                required_devtype="HDAWG",
                required_err_msg="This driver requires a HDAWG!",
            )
        return

    #################################################################
    #
    #
    #
    #
    #
    #
    # setting/getting of node values
    #################################################################
    def set_node_value(self, set_command, value):
        """sets the node value of the given node
        
        Arguments:
            set_command {string} -- node path, device does not need to be specified
            value {} -- value to be set, various datatypes
        
        Returns:
            vaious datatypes -- value actually set on device
        """
        node = (
            "/{}/".format(self.device)
            + set_command  # bring node path to format "/dev8030/.../.."
        )
        dtype = self._get_node_datatype(node)
        # set parameter
        self._set_parameter(node, dtype(value))
        return self.get_node_value(node)

    #################################################################
    def _set_parameter(self, node, value):
        """set value for given node depending on datatype
        
        Arguments:
            node {string} -- node path, device needs to be be specified
            value {various} -- actual value to be set
        """
        if isinstance(value, float):
            self.daq.asyncSetDouble(node, value)
        elif isinstance(value, int):
            self.daq.asyncSetInt(node, value)
        elif isinstance(value, str):
            self.daq.asyncSetString(node, value)
        elif isinstance(value, complex):
            self.daq.setComplex(node, value)
        return

    #################################################################
    def get_node_value(self, node):
        """method to get value of node from device
        
        Arguments:
            node {string} -- node path, device may be specified
        
        Returns:
            various -- value on device
        """
        if self.device not in node:
            node = "/{}/".format(self.device) + node
        dtype = self._get_node_datatype(node)
        # read data from ZI
        d = self.daq.get(node, True)
        assert len(d) > 0
        # extract and return data
        data = next(iter(d.values()))
        # all others
        if isinstance(data, dict) and "value" in data:
            data = data["value"]
        value = dtype(data[0])
        return value

    #################################################################
    def _get_node_datatype(self, node):
        """return datatype of node
        
        Arguments:
            node {string} -- node path, device must be specified
        
        Returns:
            dtype -- datatype of node, in {str, int, float, complex}
        """
        # used cached value, if available
        if not hasattr(self, "_node_datatypes"):
            self._node_datatypes = dict()
        if node in self._node_datatypes:
            return self._node_datatypes[node]
        # find datatype from returned data
        d = self.daq.get(node, True)
        assert len(d) > 0
        data = next(iter(d.values()))
        # if returning dict, strip timing information (API level 6)
        if isinstance(data, list):
            data = data[0]
        if isinstance(data, dict) and "value" in data:
            data = data["value"]
        if isinstance(data, dict) and "vector" in data:
            data = data["vector"]
        # get first item, if python list assume string
        if isinstance(data, list):
            dtype = str
        # not string, should be np array, check dtype
        elif data.dtype in (int, np.int_, np.int64, np.int32, np.int16):
            dtype = int
        elif data.dtype in (float, np.float_, np.float64, np.float32):
            dtype = float
        elif data.dtype in (complex, np.complex_, np.complex64, np.complex128):
            dtype = complex
        # else: ERROR
        # keep track of datatype for future use
        self._node_datatypes[node] = dtype
        return dtype


#################################################################
if __name__ == "__main__":
    pass

