import numpy as np
import json
import pathlib

from .tools import InstrumentConfiguration, ZIConnection
from . import UHFQA, HDAWG, PQSC


class MultiDeviceConnection:
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
        self._shared_connection = ZIConnection(details)
        self._shared_connection.connect()

    def connect_device(self, device):
        assert isinstance(device, (HDAWG, UHFQA, PQSC))
        device.setup(connection=self._shared_connection)
        device.connect_device()
        if isinstance(device, HDAWG):
            self._hdawgs[device.name] = device
        if isinstance(device, UHFQA):
            self._uhfqas[device.name] = device
        if isinstance(device, PQSC):
            self._pqsc = device

    @property
    def hdawgs(self):
        return self._hdawgs

    @property
    def uhfqas(self):
        return self._uhfqas

    @property
    def pqsc(self):
        return self._pqsc

