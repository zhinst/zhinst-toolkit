import numpy as np

from .tools import (
    DeviceConnection,
    ZIConnection,
    InstrumentConfiguration,
    ZINodetree,
    ZHTKException,
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
        self._controller = DeviceConnection(self, **kwargs)
        self._nodetree = None

    def setup(self, connection: ZIConnection = None):
        self._controller.setup(connection=connection)

    def connect_device(self, nodetree=True):
        self._controller.connect_device()
        if nodetree:
            self._nodetree = ZINodetree(self)
        self._init_settings()

    @property
    def nodetree(self):
        return self._nodetree

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
    def _set(self, *args):
        if not self.is_connected:
            raise ZHTKException(
                f"The device {self.name} ({self.serial}) is not connected to a Data Server!"
            )
        self._controller.set(*args)

    def _get(self, command, valueonly=True):
        self._check_connected()
        return self._controller.get(command, valueonly=valueonly)

    @property
    def _awg_connection(self):
        self._check_connected()
        if self.device_type not in ["hdawg", "uhfqa", "uhfli"]:
            raise ZHTKException("You cannot access AWG module of the Data Server!")
        else:
            return self._controller._connection.awg_module

    def _get_nodetree(self, prefix, **kwargs):
        self._check_connected()
        return self._controller.get_nodetree(prefix, **kwargs)

    def _check_connected(self):
        if not self.is_connected:
            raise ZHTKException(
                f"The device {self.name} ({self.serial}) is not connected to a Data Server!"
            )
