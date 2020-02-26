from .device import Device


class PQSC(Device):
    @property
    def device_type(self):
        return "pqsc"
