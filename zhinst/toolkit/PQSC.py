import numpy as np

from .Base import BaseController
from .connection import ZIDeviceConnection


"""
High-level controller for PQSC.

"""


class PQSC:
    def __init__(self):
        self.__name = "pqsc0"
        self._controller = PQSCController()

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup("connection-pqsc.json", connection=connection)

    def connect_device(self, address, interface):
        self._controller.connect_device(self.__name, address, interface)
        self.__init_settings()

    def __init_settings(self):
        pass

    # device specific methods

    # wrap around get and set of Controller
    def set(self, *args):
        self._controller.set(self.__name, *args)

    def get(self, command, valueonly=True):
        return self._controller.get(self.__name, command, valueonly=valueonly)


class PQSCController(BaseController):
    pass
