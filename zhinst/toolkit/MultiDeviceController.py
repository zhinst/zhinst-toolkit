import numpy as np
import json
import pathlib

from .tools import InstrumentConfiguration, ZIDeviceConnection
from . import UHFQA, HDAWG, PQSC


class MultiDeviceController:
    def __init__(self):
        self._shared_connection = None
        self._config = None
        self._hdawgs = dict()
        self._uhfqas = dict()
        self._pqsc = None

    def setup(self, **kwargs):
        config = InstrumentConfiguration()
        config.api_config.host = kwargs.get("host", "localhost")
        config.api_config.port = kwargs.get("port", 8004)
        config.api_config.api = kwargs.get("api", 6)
        self._config = config
        details = self._config.api_config
        self._shared_connection = ZIDeviceConnection(details)
        self._shared_connection.connect()

    def connect_hdawg(self, name, address, interface):
        device = HDAWG(name)
        device.setup(connection=self._shared_connection)
        device.connect_device(address, interface)
        self._hdawgs[name] = device
        print(f"Added HDAWG: {name}")

    def connect_uhfqa(self, name, address, interface):
        device = UHFQA(name)
        device.setup(connection=self._shared_connection)
        device.connect_device(address, interface)
        self._uhfqas[name] = device
        print(f"Added UHFQA: {name}")

    def connect_pqsc(self, name, address, interface):
        device = PQSC(name)
        device.setup(connection=self._shared_connection)
        device.connect_device(address, interface)
        self._pqsc = device
        print(f"Added PQSC")

    @property
    def hdawgs(self):
        return self._hdawgs

    @property
    def uhfqas(self):
        return self._uhfqas

    @property
    def pqsc(self):
        return self._pqsc

