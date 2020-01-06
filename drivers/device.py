import zhinst
import zhinst.utils
import numpy as np


class DeviceTypeError(Exception):
    pass



class Device(object):
    """ZiDevice class that implements basic functionality common to any ZI device
    
    Attributes:
        daq {ziDAQmodule} -- ziPython DAQ module used for the data connection
        device {string} -- device string, e.g. "dev8030"
    
    Public Methods:
        connect(self, address, device_type)
        set_node_value(self, node, value)
        get_node_value(self, node)

    Typical Usage:
        device = Device()
        device.connect("dev8030", "HDAWG")
        device.set_node_value("sigouts/0/on", 1)
        device.get_node_value("sigouts/0/on")

    """

    def connect(self, address, device_type=None, port=8004, api_level=6):
        """open connection to HDAWG device, initialize DAQ object
        
        Arguments:
            object {self} -- self
            address {string} -- device address, e.g. "dev8030"
            device_type {string} -- required device type, e.g. {"HDAWG", "UHFQA"}
        
        Keyword Arguments:
            port {int} -- default port to discover device (default: {8004})
            api_level {int} -- ziPython API level (default: {6})
        """
        if address == "":
            self._daq = zhinst.utils.autoConnect(
                default_port=port, api_level=api_level
            )
            self._device = zhinst.utils.autoDetect(self._daq)
        else:
            if device_type is None:
                raise DeviceTypeError("Device type must be specified")
            (self._daq, self._device, _) = zhinst.utils.create_api_session(
                address,
                api_level,
                required_devtype=device_type,
                required_err_msg="This driver requires a {}!".format(device_type),
            )
        return

    def set_node(self, set_command, value):
        """sets the node value of the given node
        
        Arguments:
            set_command {string} -- node path, device does not need to be specified
            value {} -- value to be set, various datatypes
        
        Returns:
            vaious datatypes -- value actually set on device
        """
        node = self._command_to_node(set_command)
        if "/zi/" in set_command.lower():
            node = set_command
        dtype = self.__get_node_datatype(node)
        self.__set_parameter(node, dtype(value))
        return self.get_node(node)

    def __set_parameter(self, node, value):
        """set value for given node depending on datatype
        
        Arguments:
            node {string} -- node path, device needs to be be specified
            value {various} -- actual value to be set
        """
        if isinstance(value, float):
            self._daq.asyncSetDouble(node, value)
        elif isinstance(value, int):
            self._daq.asyncSetInt(node, value)
        elif isinstance(value, str):
            self._daq.asyncSetString(node, value)
        elif isinstance(value, complex):
            self._daq.setComplex(node, value)
        return

    def get_node(self, get_command):
        """method to get value of node from device
        
        Arguments:
            node {string} -- node path, device may be specified
        
        Returns:
            various -- value on device
        """
        node = self._command_to_node(get_command)
        dtype = self.__get_node_datatype(node)
        # read data from ZI
        d = self._daq.get(node, flat=True)
        assert len(d) > 0
        # extract and return data
        data = next(iter(d.values()))
        # all others
        if isinstance(data, dict) and "value" in data:
            data = data["value"]
        value = dtype(data[0])
        return value

    def __get_node_datatype(self, node):
        """return datatype of node
        
        Arguments:
            node {string} -- node path, device must be specified
        
        Returns:
            dtype -- datatype of node, in {str, int, float, complex}
        """
        # used cached value, if available
        if not hasattr(self, "_node_datatypes"):
            self.__node_datatypes = dict()
        if node in self.__node_datatypes:
            return self.__node_datatypes[node]
        # find datatype from returned data
        d = self._daq.get(node, flat=True)
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
        else: 
            raise Exception("Node data type not recognized!")
        # keep track of datatype for future use
        self.__node_datatypes[node] = dtype
        return dtype

    def _command_to_node(self, command):
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self._device not in command:
                command = "/{}".format(self._device) + command
        return command