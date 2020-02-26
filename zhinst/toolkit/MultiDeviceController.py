import numpy as np
import json
import pathlib

from .tools.interface import InstrumentConfiguration
from .tools.connection import ZIDeviceConnection
from .tools.devices import Factory
from .tools import BaseController
from .UHFQA import UHFQA
from .HDAWG import HDAWG
from .PQSC import PQSC


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
        device = HDAWG()
        device.setup(connection=self._shared_connection)
        device.connect_device(address, interface)
        self.hdawgs[name] = device
        print(f"Added HDAWG: {name}")

    def connect_uhfqa(self, name, address, interface):
        device = UHFQA()
        device.setup(connection=self._shared_connection)
        device.connect_device(address, interface)
        self.uhfqas[name] = device
        print(f"Added UHFQA: {name}")

    def connect_pqsc(self, address, interface):
        device = PQSC()
        device.setup(connection=self._shared_connection)
        device.connect_device(address, interface)
        self.pqsc = device
        print(f"Added PQSC")

    ####################################################
    # device specific methods
