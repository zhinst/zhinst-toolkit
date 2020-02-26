from .device import Device
from .awg import AWG


class HDAWG(Device):
    def __init__(self, device):
        super().__init__(device)

        for i in range(4):
            self._awgs[i] = AWG(i, self)

    @property
    def device_type(self):
        return "hdawg"
