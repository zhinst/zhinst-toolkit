import numpy as np

from .tools import BaseController, ZIDeviceConnection


"""
High-level controller for PQSC.

"""


class PQSC:
    def __init__(self, name):
        self._name = name
        self._controller = PQSCController()

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup(connection=connection)

    def connect_device(self, address, interface):
        self._controller.connect_device(self.name, "pqsc", address, interface)
        self._init_settings()

    @property
    def name(self):
        return self._name

    def _init_settings(self):
        pass

    # device specific methods

    # wrap around get and set of Controller
    def set(self, *args):
        self._controller.set(self.name, *args)

    def get(self, command, valueonly=True):
        return self._controller.get(self.name, command, valueonly=valueonly)

    def get_nodetree(self, prefix, **kwargs):
        return self._controller.get_nodetree(prefix, **kwargs)


class PQSCController(BaseController):
    pass
