import attr


@attr.s
class ZIDeviceConfig:
    serial: str = attr.ib(default="dev#####")
    device_type: str = attr.ib(
        default="hdawg", validator=attr.validators.in_(["hdawg", "uhfqa", "pqsc"])
    )
    interface: str = attr.ib(default="1GbE")


class ZIDevice:
    def __init__(self):
        self._config = ZIDeviceConfig()
        self.name = "device0"

    @property
    def config(self):
        return self._config


@attr.s
class ZIAPI:
    host: str = attr.ib(default="localhost")
    port: int = attr.ib(default=8004)
    api: int = attr.ib(default=6)


class InstrumentConfiguration:
    def __init__(self):
        self._api_config = ZIAPI()
        self._instrument = ZIDevice()

    @property
    def api_config(self):
        return self._api_config

    @property
    def instrument(self):
        return self._instrument
