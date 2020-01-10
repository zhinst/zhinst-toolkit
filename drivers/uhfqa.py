from .device import Device
from .awg import AWG


class UHFQA(Device):
    def __init__(self):
        self.__awg = AWG()

    def connect(self, device):
        super().connect(device, "UHFQA")

    def disconnect(self):
        pass

    def setup_awg(self):
        self.__awg.setup(self._daq, self._device)
        print(f"Started AWG of device {self._device}")

    @property
    def awg(self):
        return self.__awg
