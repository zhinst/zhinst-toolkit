import copy

# from qccs.helpers import Node


class Device(object):
    def __init__(self, device, parent=None):
        self._awgs = {}
        self._name = device.name
        self._config = copy.deepcopy(device.config)
        # super().__init__(name=self._name, parent=parent)

    @property
    def serial(self):
        return self._config.serial

    @property
    def interface(self):
        return self._config.interface
