import json
import time

from .drivers.connection import ZIDeviceConnection
from .drivers.devices.factory import Factory
from helpers import SequenceProgram, Waveform
from interface import InstrumentConfiguration
from compiler import Compiler


class Controller(object):
    def __init__(self):
        self.__connection = None
        self.__instrument_config = None
        self.__device = None
        self.__compiler = None

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
        dev = devices[0]  # support only one device for now
        if dev.name == name:
            self.__device = Factory.configure_device(dev)
            self.__connection.connect_device(
                serial=self.__device.serial, interface=self.__device.interface
            )
            self.__compiler = Compiler(dev)
        else:
            raise Exception("Device not found in Instrument Configuration!")

    def compile_program(self, awg):
        self.__connection.awgModule.update(index=awg, device=self.__device.serial)
        if self.__compiler.sequence_type(awg) == "Simple":
            buffer_lengths = [
                w.buffer_length for w in self.__device.awgs[awg].waveforms
            ]
            self.__compiler.set_parameter(awg, buffer_lengths=buffer_lengths)
        self.__update_awg_program(awg)
        program = self.__device.awgs[awg].get_program()
        self.__connection.awgModule.set("compiler/sourcestring", program)
        while self.__connection.awgModule.get_int("compiler/status") == -1:
            time.sleep(0.1)
        if self.__connection.awgModule.get_int("compiler/status") == 1:
            raise Exception(
                "Upload failed: \n"
                + self.__connection.awgModule.get_string("compiler/statusstring")
            )
        if self.__connection.awgModule.get_int("compiler/status") == 2:
            raise Warning(
                "Compiled with warning: \n"
                + self.__connection.awgModule.get_string("compiler/statusstring")
            )
        if self.__connection.awgModule.get_int("compiler/status") == 2:
            print("Compilation successful")
        self.__wait_upload_done(awg)

    def awg_run(self, awg):
        self.set(f"/awgs/{awg}/enable", 1)
        print(f"Started AWG {awg}!")

    def awg_stop(self, awg):   
        self.set(f"/awgs/{awg}/enable", 0)
        print(f"Stopped AWG {awg}!")

    def awg_is_running(self, awg):
        return bool(self.__connection.awgModule.get_int("awg/enable", index=awg))
    
    def awg_queue_waveform(self, awg, waveform: Waveform, **kwargs):
        if self.__compiler.sequence_type(awg) != "Simple":
            raise Exception("Waveform upload only possible for 'Simple' sequence!")
        self.__device.awgs[awg].waveforms.append(waveform)
        print(f"current length of queue: {len(self.__device.awgs[awg].waveforms)}")

    def awg_upload_waveforms(self, awg):
        waveform_data = [w.data for w in self.__device.awgs[awg].waveforms]
        self.compile_program(awg)
        nodes = [f"awgs/{awg}/waveform/waves/{i}" for i in range(len(waveform_data))]
        self.set(zip(nodes, waveform_data))
        self.__device.awgs[awg].reset_waveforms()

    def awg_set_sequence_params(self, awg, **kwargs):
        self.__compiler.set_parameter(awg, **kwargs)
        self.__update_awg_program(awg)

    def __update_awg_program(self, awg):
        program = self.__compiler.get_program(awg)
        self.__device.awgs[awg].set_program(program)

    def __wait_upload_done(self, awg, timeout=10):
        time.sleep(0.01)
        node = f"/{self.__device.serial}/awgs/{awg}/sequencer/status"
        tik = time.time()
        while self.get(node):
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise Exception("Program upload timed out!")
        print(f"Sequencer status: {'Uploaded' if not self.get(node) else 'FAILED!!'}")

    def compiler_list_params(self, awg):
        return self.__compiler.list_params(awg)


    # set and get here ...
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

