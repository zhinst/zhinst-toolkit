import copy


class Device:
    def __init__(self, device, parent=None):
        self._awgs = {}
        self._name = device.name
        self._config = copy.deepcopy(device.config)

    @property
    def name(self):
        return self._name

    @property
    def serial(self):
        return self._config.serial

    @property
    def interface(self):
        return self._config.interface

    @property
    def awgs(self):
        return self._awgs
