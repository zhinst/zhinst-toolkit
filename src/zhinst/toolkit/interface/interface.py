# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import attr
from enum import Enum


class DeviceTypes(Enum):
    """Enum of device types."""

    HDAWG = "hdawg"
    UHFQA = "uhfqa"
    UHFLI = "uhfli"
    MFLI = "mfli"
    PQSC = "pqsc"
    SHFQA = "shfqa"


@attr.s
class ZIDeviceConfig:
    """Device configuration with serial, device_type and interface."""

    serial: str = attr.ib(default="dev#####")
    device_type: str = attr.ib(default=DeviceTypes.HDAWG)
    interface: str = attr.ib(default="1GbE")


class ZIDevice:
    """Device configuration with name and config."""

    def __init__(self):
        self._config = ZIDeviceConfig()
        self.name = "device0"

    @property
    def config(self):
        return self._config


@attr.s
class ZIAPI:
    """API configuration with host, port, api-level."""

    host: str = attr.ib(default="localhost")
    port: int = attr.ib(default=8004)
    api: int = attr.ib(default=6)


class InstrumentConfiguration:
    """Data structure used to for instrument and API configuration."""

    def __init__(self):
        self._api_config = ZIAPI()
        self._instrument = ZIDevice()

    @property
    def api_config(self):
        return self._api_config

    @property
    def instrument(self):
        return self._instrument
