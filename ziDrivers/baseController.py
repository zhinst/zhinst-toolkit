import json
import time
import pathlib

from .connection import ZIDeviceConnection
from .devices import Factory
from .interface import InstrumentConfiguration


class BaseController(object):
    def __init__(self):
        self._connection = None
        self._instrument_config = None
        self._devices = None

    def setup(self, filename, connection: ZIDeviceConnection = None):
        dir = pathlib.Path(__file__).parent
        instrument_config = dir / "resources" / filename
        try:
            with open(instrument_config) as file:
                data = json.load(file)
                schema = InstrumentConfiguration()
                self._instrument_config = schema.load(data)
            if connection is None:
                for i in self._instrument_config.api_configs:
                    if i.provider == "zi":
                        self._connection = ZIDeviceConnection(i.details)
            else:
                self._connection = connection
            self._connection.connect()
        except IOError:
            print(f"File {instrument_config} is not accessible")

    def connect_device(self, name, address, interface):
        devices = self._instrument_config.instruments[0].setup
        for dev in devices:
            if self._devices is None:
                self._devices = dict()
            if dev.name == name:
                dev.config.serial = address
                dev.config.interface = interface
                self._devices[name] = Factory.configure_device(dev)
                self._connection.connect_device(
                    serial=self._devices[name].serial,
                    interface=self._devices[name].interface,
                )
        if name not in self._devices.keys():
            raise Exception("Device not found in Instrument Configuration!")

    def set(self, name, *args):
        if self._devices is not None:
            if len(args) == 2:
                settings = [(args[0], args[1])]
            elif len(args) == 1:
                settings = args[0]
            else:
                raise Exception("Invalid number of arguments!")
            settings = self.__commands_to_node(name, settings)
            return self._connection.set(settings)
        else:
            raise Exception("No device connected!")

    def get(self, name, command, valueonly=True):
        if self._devices is not None:
            if isinstance(command, list):
                paths = []
                for c in command:
                    paths.append(self.__command_to_node(name, c))
                node_string = ", ".join([p for p in paths])
            elif isinstance(command, str):
                node_string = self.__command_to_node(name, command)
            else:
                raise Exception("Invalid argument!")
            data = self._connection.get(node_string, settingsonly=False, flat=True)
            data = self.__get_value_from_dict(name, data)
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

    def __get_value_from_dict(self, name, data):
        if not isinstance(data, dict):
            raise Exception("Something went wrong...")
        if not len(data):
            raise Exception("No data returned... does the node exist?")
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace(f"/{self._devices[name].serial}/", "")
            if isinstance(data_dict, list):
                data_dict = data_dict[0]
            if "value" in data_dict.keys():
                new_data[key] = data_dict["value"][0]
            if "vector" in data_dict.keys():
                new_data[key] = data_dict["vector"]
        return new_data

    def __commands_to_node(self, name, settings):
        new_settings = []
        for args in settings:
            try:
                if len(args) != 2:
                    raise Exception("node/value must be specified as pairs!")
            except TypeError:
                raise Exception("node/value must be specified as pairs!")
            new_settings.append((self.__command_to_node(name, args[0]), args[1]))
        return new_settings

    def __command_to_node(self, name, command):
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self._devices[name].serial not in command:
                command = f"/{self._devices[name].serial}" + command
        return command
