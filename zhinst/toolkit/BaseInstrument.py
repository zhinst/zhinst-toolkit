import numpy as np

from .tools import (
    Controller,
    ZIDeviceConnection,
    InstrumentConfiguration,
)


"""
High-level controller for UHFQA.

"""


class BaseInstrument:
    def __init__(self, name, device_type, serial, **kwargs):
        self._config = InstrumentConfiguration()
        self._config._instrument._name = name
        self._config._instrument._config._device_type = device_type
        self._config._instrument._config._serial = serial
        self._config._instrument._config._interface = kwargs.get("interface", "1GbE")
        self._controller = Controller(self, **kwargs)

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup(connection=connection)

    def connect_device(self):
        self._controller.connect_device()
        self._init_settings()

    @property
    def name(self):
        return self._config._instrument._name

    @property
    def device_type(self):
        return self._config._instrument._config._device_type

    @property
    def serial(self):
        return self._config._instrument._config._serial

    @property
    def interface(self):
        return self._config._instrument._config._interface

    @property
    def is_connected(self):
        return not self._controller._connection is None

    def _init_settings(self):
        pass

    # wrap around get and set of Controller
    def set(self, *args):
        if not self.is_connected:
            raise Exception(
                f"The device {self.name} ({self.serial}) is not connected to a Data Server!"
            )
        self._controller.set(*args)

    def get(self, command, valueonly=True):
        self._check_connected()
        return self._controller.get(command, valueonly=valueonly)

    @property
    def awg_connection(self):
        self._check_connected()
        if self.device_type not in ["hdawg", "uhfqa", "uhfli"]:
            raise Exception("You cannot access AWG module of the Data Server!")
        else:
            return self._controller._connection.awg_module

    def get_nodetree(self, prefix, **kwargs):
        self._check_connected()
        return self._controller.get_nodetree(prefix, **kwargs)

    def _check_connected(self):
        if not self.is_connected:
            raise Exception(
                f"The device {self.name} ({self.serial}) is not connected to a Data Server!"
            )
