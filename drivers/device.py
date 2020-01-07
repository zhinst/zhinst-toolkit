import zhinst
import zhinst.utils
import numpy as np


class DeviceTypeError(Exception):
    pass



class Device(object):
    def connect(self, address, device_type=None, port=8004, api_level=6):
        if address == "":
            self.__daq = zhinst.utils.autoConnect(
                default_port=port, api_level=api_level
            )
            self._device = zhinst.utils.autoDetect(self.__daq)
        else:
            if device_type is None:
                raise DeviceTypeError("Device type must be specified")
            (self.__daq, self._device, _) = zhinst.utils.create_api_session(
                address,
                api_level,
                required_devtype=device_type,
                required_err_msg="This driver requires a {}!".format(device_type),
            )
        return

    def set(self, *args):
        if len(args) == 2:
            settings = [(args[0], args[1])]
        elif len(args) == 1:
            settings = args[0]
        else:
            raise Exception("Invalid number of arguments!")
        settings = self.__commands_to_node(settings)
        return self.__daq.set(settings)

    def get_node(self, get_command):
        node = self.__command_to_node(get_command)
        dtype = self.__get_node_datatype(node)
        # read data from ZI
        d = self.__daq.get(node, flat=True)
        assert len(d) > 0
        # extract and return data
        data = next(iter(d.values()))
        # all others
        if isinstance(data, dict) and "value" in data:
            data = data["value"]
        value = dtype(data[0])
        return value

    def __get_node_datatype(self, node):
        # used cached value, if available
        if not hasattr(self, "_node_datatypes"):
            self.__node_datatypes = dict()
        if node in self.__node_datatypes:
            return self.__node_datatypes[node]
        # find datatype from returned data
        d = self.__daq.get(node, flat=True)
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

    
    def __commands_to_node(self, settings):
        new_settings = []
        for args in settings:
            new_settings.append( (self.__command_to_node(args[0]), args[1]) )
        return new_settings
    
    
    def __command_to_node(self, command):
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self._device not in command:
                command = "/{}".format(self._device) + command
        return command