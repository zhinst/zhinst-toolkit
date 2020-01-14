import json

from .drivers.connection import ZIDeviceConnection
from .drivers.devices.factory import Factory
from interface import InstrumentConfiguration


class Controller(object):
    def __init__(self):
        self.__connection = None
        self.__instrument_config = None
        self.__device = None

    def setup(self, instrument_config):
        try:
            with open(instrument_config) as file:
                data = json.load(file)
                schema = InstrumentConfiguration()
                self.__instrument_config = schema.load(data)
            for i in self.__instrument_config.api_configs:
                if i.provider == "zi":
                    self.__connection = ZIDeviceConnection(i.details)
            self.__connection.connect()
        except IOError:
            print(f"File {instrument_config} is not accessible")

    def connect_device(self, name):
        devices = self.__instrument_config.instruments[0].setup
        for dev in devices:
            if dev.name == name:
                self.__device = Factory.configure_device(dev)
                self.__connection.connect_device(
                    serial=self.__device.serial, interface=self.__device.interface
                )
            else:
                raise Exception("Device not found in Instrument Configuration!")

    def set(self, *args):
        if self.__device is not None:
            if len(args) == 2:
                settings = [(args[0], args[1])]
            elif len(args) == 1:
                settings = args[0]
            else:
                raise Exception("Invalid number of arguments!")
            settings = self.__commands_to_node(settings)
            self.__connection.set(settings)
        else:
            raise Exception("No device connected!")

    def get(self, command, valueonly=True):
        if self.__device is not None:
            if isinstance(command, list):
                paths = []
                for c in command:
                    paths.append(self.__command_to_node(c))
                node_string = ", ".join([p for p in paths])
            elif isinstance(command, str):
                node_string = self.__command_to_node(command)
            else:
                raise Exception("Invalid argument!")
            data = self.__connection.get(node_string, settingsonly=False, flat=True)
            data = self.__get_value_from_dict(data)
            if valueonly:
                if len(data) > 1:
                    return [v for v in data.values()]
                else:
                    return list(data.values())[0]
            else:
                return data
        else:
            raise Exception("No device connected!")

    def __get_value_from_dict(self, data):
        if not isinstance(data, dict):
            raise Exception("Something went wrong...")
        if not len(data):
            raise Exception("No data returned... does the node exist?")
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace(f"/{self.__device.serial}/", "")
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
            if self.__device.serial not in command:
                command = f"/{self.__device.serial}" + command
        return command


###################################################################

# def set(self, **settings):
#         self.__sequence.set(**settings)

#     def update(self):
#         if self.__sequence.sequence_type == "Simple":
#             if len(self.__waveforms) == 0:
#                 raise Exception("No Waveforms defined!")
#             self.__sequence.set(
#                 buffer_lengths=[w.buffer_length for w in self.__waveforms]
#             )
#         self._upload_program(self.__sequence.get())
#         print("Uploaded sequence program to device!")

#     def add_waveform(self, wave1, wave2):
#         if self.__sequence.sequence_type == "Simple":
#             w = Waveform(wave1, wave2)
#             self.__waveforms.append(w)
#         else:
#             print("AWG Sequence type must be 'Simple' to upload waveforms!")

#     def upload_waveforms(self):
#         self.update()
#         for i, w in enumerate(self.__waveforms):
#             self._upload_waveform(w, i)
#         print(f"Finished uploading {len(self.__waveforms)} waveforms!")
#         self.__waveforms = []


#         self.__awg.set(target="UHFQA", clock_rate=1.8e9)
