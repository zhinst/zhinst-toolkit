# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import json
import pathlib

from zhinst.toolkit.interface import InstrumentConfiguration
from zhinst.toolkit.control.connection import ZIConnection
from zhinst.toolkit.control.drivers import UHFQA, HDAWG, PQSC, UHFLI, MFLI
from zhinst.toolkit.control.drivers.base import ZHTKException


class MultiDeviceConnection:
    def __init__(self):
        self._shared_connection = None
        self._config = None
        self._hdawgs = {}
        self._uhfqas = {}
        self._uhflis = {}
        self._mflis = {}
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
        if isinstance(device, HDAWG):
            self._hdawgs[device.name] = device
        elif isinstance(device, UHFQA):
            self._uhfqas[device.name] = device
        elif isinstance(device, PQSC):
            self._pqsc = device
        elif isinstance(device, UHFLI):
            self._uhflis = device
        elif isinstance(device, MFLI):
            self._mflis = device
        else:
            raise ZHTKException("This device is not recognized!")
        device.setup(connection=self._shared_connection)
        device.connect_device()

    @property
    def hdawgs(self):
        return self._hdawgs

    @property
    def uhfqas(self):
        return self._uhfqas

    @property
    def pqsc(self):
        return self._pqsc

    @property
    def uhflis(self):
        return self._uhflis

    @property
    def mflis(self):
        return self._mflis
