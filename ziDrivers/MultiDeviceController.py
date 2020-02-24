import numpy as np
import json
import pathlib

from .interface import InstrumentConfiguration
from .connection import ZIDeviceConnection
from .devices import Factory
from .baseController import BaseController
from .UHFQAController import UHFQAController
from .HDAWGController import HDAWGController



class MultiDeviceController(object):
    def __init__(self):
        self._shared_connection = None
        self._instrument_config = None
        self.hdawgs = dict()
        self.uhfqas = dict()
    
    def setup(self):
        filename = "connection-hd-qa.json"
        dir = pathlib.Path(__file__).parent
        instrument_config = dir / "resources" / filename
        try:
            with open(instrument_config) as file:
                data = json.load(file)
                schema = InstrumentConfiguration()
                self._instrument_config = schema.load(data)
            for i in self._instrument_config.api_configs:
                if i.provider == "zi":
                    self._shared_connection = ZIDeviceConnection(i.details)
            self._shared_connection.connect()
        except IOError:
            print(f"File {instrument_config} is not accessible")

    def connect_hdawg(self, name, address, interface):
        device = HDAWGController()
        device.set_device_connection(self._shared_connection)
        device.connect_device(address, interface)
        self.hdawgs[name] = device
        print(f"Added HDAWG: {name}")

    def connect_uhfqa(self, name, address, interface):
        device = UHFQAController()
        device.set_device_connection(self._shared_connection)
        device.connect_device(address, interface)
        self.uhfqas[name] = device
        print(f"Added UHFQA: {name}")
        


        



    ####################################################
    # device specific methods
