from .device import Device
from .awg import AWG


class UHFQA(Device):
    def __init__(self, device):
        super().__init__(device)
        for i in self._connectivity.awgs:
            self._awgs[i.awg] = AWG(i, self)
