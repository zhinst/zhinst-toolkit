import json
import time
import pathlib

from ..connection import ZIDeviceConnection
from ..devices import Factory
from ..interface import InstrumentConfiguration


class BaseController(object):
    def __init__(self, name, device_type, serial, **kwargs):
        self._connection = None
        config = InstrumentConfiguration()
        config.instrument.name = name
        config.instrument.config.serial = serial
        config.instrument.config.device_type = device_type
        config.instrument.config.interface = kwargs.get("interface", "1GbE")
        config.api_config.host = kwargs.get("host", "localhost")
        config.api_config.port = kwargs.get("port", 8004)
        config.api_config.api = kwargs.get("api", 6)
        self._config = config
        self._device = Factory.configure_device(self._config.instrument)

    def setup(self, connection: ZIDeviceConnection = None):
        if connection is None:
            details = self._config.api_config
            self._connection = ZIDeviceConnection(details)
        else:
            self._connection = connection
        self._connection.connect()

    def connect_device(self, name, device_type, serial, interface):
        self._connection.connect_device(
            serial=self._device.serial, interface=self._device.interface,
        )

    def set(self, *args):
        if self._device is not None:
            if len(args) == 2:
                settings = [(args[0], args[1])]
            elif len(args) == 1:
                settings = args[0]
            else:
                raise Exception("Invalid number of arguments!")
            settings = self._commands_to_node(settings)
            return self._connection.set(settings)
        else:
            raise Exception("No device connected!")

    def get(self, command, valueonly=True):
        if self._device is not None:
            if isinstance(command, list):
                paths = []
                for c in command:
                    paths.append(self._command_to_node(c))
                node_string = ", ".join([p for p in paths])
            elif isinstance(command, str):
                node_string = self._command_to_node(command)
            else:
                raise Exception("Invalid argument!")
            data = self._connection.get(node_string, settingsonly=False, flat=True)
            data = self._get_value_from_dict(data)
            if valueonly:
                if len(data) > 1:
                    return [v for v in data.values()]
                else:
                    return list(data.values())[0]
            else:
                return data
        else:
            raise Exception("No device connected!")

    def get_nodetree(self, prefix: str, **kwargs):
        return json.loads(self._connection.list_nodes(prefix, **kwargs))

    def _get_value_from_dict(self, data):
        if not isinstance(data, dict):
            raise Exception("Something went wrong...")
        if not len(data):
            raise Exception("No data returned... does the node exist?")
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace(f"/{self._device.serial}/", "")
            if isinstance(data_dict, list):
                data_dict = data_dict[0]
            if "value" in data_dict.keys():
                new_data[key] = data_dict["value"][0]
            if "vector" in data_dict.keys():
                new_data[key] = data_dict["vector"]
        return new_data

    def _commands_to_node(self, settings):
        new_settings = []
        for args in settings:
            try:
                if len(args) != 2:
                    raise Exception("node/value must be specified as pairs!")
            except TypeError:
                raise Exception("node/value must be specified as pairs!")
            new_settings.append((self._command_to_node(args[0]), args[1]))
        return new_settings

    def _command_to_node(self, command):
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self._device.serial not in command:
                command = f"/{self._device.serial}" + command
        return command
