from .device import Device
from .awg import AWG


class HDAWG(Device):
    def __init__(self, hdawg8=True, **kwargs):
        self.__n_channels = 8 if hdawg8 else 4
        self.__awgs = []
        for i in range(int(self.__n_channels / 2)):
            self.__awgs.append(AWG(index=i))
        pass

    def connect(self, device):
        super().connect(device, "HDAWG")

    def disconnect(self):
        pass

    def setup_awg(self, i):
        self.__awgs[i].setup(self._daq, self._device)
        print(f"Started AWG {i} of device {self._device}")

    @property
    def awgs(self):
        return self.__awgs

