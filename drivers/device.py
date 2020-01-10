import zhinst
import zhinst.utils
import numpy as np
import networkx as nx


class DeviceTypeError(Exception):
    pass


class Device(object):
    def __init__(self, **kwargs):
        if "name" not in kwargs:
            raise Exception("A device needs a name")
        self.__name = kwargs.get("name")
        self.__serial = self.__interface = str()
        self.__graph = nx.DiGraph()
        self.__component = True if kwargs.get("main_component") == "true" else False
        self.__graph.add_node(
            kwargs["name"], device=self, main_component=self.__component
        )
        self.__labels = (
            {self.__name: self.__name}
            if "label" not in kwargs
            else {self.__name: kwargs["label"]}
        )

        if self.__component is True:
            self.__serial = kwargs["properties"]["config"]["serial"]
            self.__interface = kwargs["properties"]["config"]["interface"]

    def add_node(self, **kwargs: dict) -> None:
        self.__labels[kwargs["name"]] = (
            kwargs["name"] if "label" not in kwargs else kwargs["label"]
        )
        self.add_edge(self.__name, kwargs["name"])

    def add_edge(self, src, dst):
        self.__graph.add_edge(src, dst)

    @property
    def graph(self):
        return self.__graph

    @property
    def labels(self):
        return self.__labels

    @property
    def name(self):
        return self.__name

    @property
    def serial(self):
        return self.__serial

    @property
    def interface(self):
        return self.__interface

    def compose(self, other_graph):
        self.__graph = nx.compose(self.__graph, other_graph)

    def update_labels(self, labels):
        self.__labels.update(labels)

    # def connect(self, address, device_type=None, port=8004, api_level=6):
    #     if address == "":
    #         self._daq = zhinst.utils.autoConnect(
    #             default_port=port, api_level=api_level
    #         )
    #         self._device = zhinst.utils.autoDetect(self._daq)
    #     else:
    #         if device_type is None:
    #             raise DeviceTypeError("Device type must be specified")
    #         (self._daq, self._device, _) = zhinst.utils.create_api_session(
    #             address,
    #             api_level,
    #             required_devtype=device_type,
    #             required_err_msg=f"This driver requires a {device_type}!"
    #         )
    #     return

    # set and get node values here ...

    def set(self, *args):
        if len(args) == 2:
            settings = [(args[0], args[1])]
        elif len(args) == 1:
            settings = args[0]
        else:
            raise Exception("Invalid number of arguments!")
        settings = self.__commands_to_node(settings)
        self._daq.set(settings)
        return

    def get(self, command, valueonly=False):
        if isinstance(command, list):
            paths = []
            for c in command:
                paths.append(self.__command_to_node(c))
            node_string = ", ".join([p for p in paths])
        elif isinstance(command, str):
            node_string = self.__command_to_node(command)
        else:
            raise Exception("Invalid argument!")
        data = self._daq.get(node_string, settingsonly=False, flat=True)
        data = self.__get_value_from_dict(data)
        if valueonly:
            if len(data) > 1:
                return [v for v in data.values()]
            else:
                return list(data.values())[0]
        else:
            return data

    def __get_value_from_dict(self, data):
        if not isinstance(data, dict):
            raise Exception("Something went wrong...")
        if not len(data):
            raise Exception("No data returned... does the node exist?")
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace(f"/{self._device}/", "")
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
            new_settings.append((self.__command_to_node(args[0]), args[1]))
        return new_settings

    def __command_to_node(self, command):
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self._device not in command:
                command = f"/{self._device}" + command
        return command
