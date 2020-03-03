import json

import zhinst.ziPython as zi


class ZHTKConnectionException(Exception):
    pass


class ZIConnection:
    def __init__(self, connection_details):
        self._connection_details = connection_details
        self._daq = None
        self._awg = None

    def connect(self):
        self._daq = zi.ziDAQServer(
            self._connection_details.host,
            self._connection_details.port,
            self._connection_details.api,
        )
        if self._daq is not None:
            print(
                f"Successfully connected to data server at "
                f"{self._connection_details.host}"
                f"{self._connection_details.port} "
                f"api version: {self._connection_details.api}"
            )
            self._awg = self.AWGModule(self._daq)
        else:
            print("No connection could be established...")

    def connect_device(self, **kwargs):
        if self._daq is None:
            raise ZHTKConnectionException("No existing connection to data server")
        if not all(k for k in ["serial", "interface"]):
            raise ZHTKConnectionException(
                "To connect a Zurich Instruments' device, youd need a serial and an interface [1gbe or usb]"
            )
        serial = kwargs.get("serial")
        interface = kwargs.get("interface")
        self._daq.connectDevice(serial, interface)
        print(
            f"Successfully connected to device {serial.upper()} on interface {interface.upper()}"
        )
        self._awg.update(device=serial, index=0)

    def set(self, *args):
        return self._daq.set(*args)

    def get(self, *args, **kwargs):
        return self._daq.get(*args, **kwargs)

    def list_nodes(self, *args, **kwargs):
        return self._daq.listNodesJSON(*args, **kwargs)

    class AWGModule:
        def __init__(self, daq):
            self._awgModule = daq.awgModule()
            self._awgModule.execute()
            self._device = self._awgModule.getString("/device")
            self._index = self._awgModule.getInt("/index")

        def set(self, *args, **kwargs):
            self.update(**kwargs)
            self._awgModule.set(*args)

        def get(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.get(*args, flat=True)

        def get_int(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.getInt(*args)

        def get_double(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.getDouble(*args)

        def get_string(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.getString(*args)

        def update(self, **kwargs):
            if "device" in kwargs.keys():
                self._update_device(kwargs["device"])
            if "index" in kwargs.keys():
                self._update_index(kwargs["index"])

        def _update_device(self, device):
            if device != self.device:
                self._update_index(0)
                self._awgModule.set("/device", device)
                self._device = device

        def _update_index(self, index):
            if index != self.index:
                self._awgModule.set("/index", index)
                self._index = index

        @property
        def index(self):
            return self._index

        @property
        def device(self):
            return self._device

    @property
    def awg_module(self):
        return self._awg


class DeviceConnection(object):
    def __init__(self, device, **kwargs):
        self._connection = None
        self._device = device

    def setup(self, connection: ZIConnection = None):
        if connection is None:
            details = self._device._config._api_config
            self._connection = ZIConnection(details)
        else:
            self._connection = connection
        self._connection.connect()

    def connect_device(self):
        self._connection.connect_device(
            serial=self._device.serial, interface=self._device.interface,
        )

    def set(self, *args):
        if len(args) == 2:
            settings = [(args[0], args[1])]
        elif len(args) == 1:
            settings = args[0]
        else:
            raise ZHTKConnectionException("Invalid number of arguments!")
        settings = self._commands_to_node(settings)
        return self._connection.set(settings)

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
                raise ZHTKConnectionException("Invalid argument!")
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
            raise ZHTKConnectionException("No device connected!")

    def get_nodetree(self, prefix: str, **kwargs):
        return json.loads(self._connection.list_nodes(prefix, **kwargs))

    def _get_value_from_dict(self, data):
        if not isinstance(data, dict):
            raise ZHTKConnectionException("Something went wrong...")
        if not len(data):
            raise ZHTKConnectionException("No data returned... does the node exist?")
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
                    raise ZHTKConnectionException(
                        "node/value must be specified as pairs!"
                    )
            except TypeError:
                raise ZHTKConnectionException("node/value must be specified as pairs!")
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
