from .device import Device
from .awg import AWG


class UHFLI(Device):
    def __init__(self, device):
        super().__init__(device)
        self._awgs[0] = AWG(0, self)

    @property
    def device_type(self):
        return "uhfli"
