from .device import Device
from .awg import AWG


class HDAWG(Device):
    def __init__(self, device):
        super().__init__(device)

