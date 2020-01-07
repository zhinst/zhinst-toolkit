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
            self.__device = zhinst.utils.autoDetect(self.__daq)
        else:
            if device_type is None:
                raise DeviceTypeError("Device type must be specified")
            (self.__daq, self.__device, _) = zhinst.utils.create_api_session(
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
        self.__daq.set(settings)
        return

    def get(self, command):
        if isinstance(command, list):
            paths = []
            for c in command:
                paths.append(self.__command_to_node(c))
            node_string = ", ".join([p for p in paths])
        elif isinstance(command, str):
            node_string = self.__command_to_node(command) 
        else:
            raise Exception("Invalid argument!")
        data = self.__daq.get(node_string, settingsonly=False, flat=True)
        return self.__get_value_from_dict(data)
        
    def __get_value_from_dict(self, data):
        if not isinstance(data, dict):
            raise Exception("Something went wrong...")
        if not len(data):
            raise Exception("No data returned... does the node exist?")
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace("/{}/".format(self.__device), "")
            if isinstance(data_dict, list):
                data_dict = data_dict[0]
            if "value" in data_dict.keys():
                new_data[key] = data_dict["value"][0]
            if "vector" in data_dict.keys():
                new_data[key] = data_dict["vector"]
        return new_data
    
    def __commands_to_node(self, settings):
        new_settings = []
        for args in settings:
            try:
                if len(args) != 2: 
                    raise Exception("node/value must be specified as pairs!")
            except TypeError:
                raise Exception("node/value must be specified as pairs!")
            new_settings.append( (self.__command_to_node(args[0]), args[1]) )
        return new_settings
    
    
    def __command_to_node(self, command):
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self.__device not in command:
                command = "/{}".format(self.__device) + command
        return command