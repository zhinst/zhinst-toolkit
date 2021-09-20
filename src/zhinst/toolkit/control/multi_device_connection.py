# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import json
import pathlib

from zhinst.toolkit.interface import InstrumentConfiguration, LoggerModule
from zhinst.toolkit.control.connection import ZIConnection
from zhinst.toolkit.control.drivers import *
from zhinst.toolkit.control.drivers.base import BaseInstrument

_logger = LoggerModule(__name__)


class MultiDeviceConnection:
    """A data server connection shared by multiple devices.

    A container for devices that ensures a single instrument connection
    (Data Server) is shared between multiple devices. The
    :class:`MultiDeviceConnection` holds dictionaries of different device types.
    The devices are identified by the name they are given. The
    *MultiDeviceConnection* connects to a Data Server with `mdc.setup()` ...

        >>> import zhinst.toolkit as tk
        >>> mdc = tk.MultiDeviceConnection(host="localhost")
        >>> mdc.setup()
        Successfully connected to data server at localhost8004 api version: 6

    and individual devices are added with `mdc.connect_device()`.

        >>> mdc.connect_device(tk.HDAWG("hdawg 1", "dev1234"))
        >>> mdc.connect_device(tk.HDAWG("hdawg 2", "dev5678"))
        >>> mdc.connect_device(tk.UHFQA("uhfqa 1", "dev9999"))
        Successfully connected to device DEV1234 on interface 1GBE
        Successfully connected to device DEV5678 on interface 1GBE
        Successfully connected to device DEV9999 on interface 1GBE

    The :class:`MultiDeviceConnection` holds dictionaries for every device type
    with the device name as keys:

        >>> hdawg1 = mdc.hdawgs["hdawg 1"]
        >>> hdawg2 = mdc.hdawgs["hdawg 2"]
        >>> uhfqa = mdc.uhfqas["uhfqa 1"]
        >>> ...


    Keyword Arguments:
        host (str): the host of the data server (default: 'localhost')
        port (int): the port for the data server (default: 8004)
        api (int): the API level for the data server (default: 6)

    Attributes:
        hdawgs (dict): A dictionary of :class:`HDAWG` s with the device names as
            keys.
        uhfqas (dict): A dictionary of :class:`UHFQA` s with the device names as
            keys.
        uhflis (dict): A dictionary of :class:`UHFLI` s with the device names as
            keys.
        mflis (dict): A dictionary of :class:`MFLI` s with the device names as
            keys.
        pqsc (:class:`PQSC`): A PQSC if one is added, otherwise None

    Raises:
        ToolkitError: if an unknown device is added

    """

    def __init__(self, **kwargs) -> None:
        self._shared_connection = None
        self._hdawgs = {}
        self._uhfqas = {}
        self._uhflis = {}
        self._mflis = {}
        self._pqsc = None
        self._shfqas = {}
        self._shfsgs = {}
        config = InstrumentConfiguration()
        config.api_config.host = kwargs.get("host", "localhost")
        config.api_config.port = kwargs.get("port", 8004)
        config.api_config.api = kwargs.get("api", 6)
        self._config = config

    def setup(self) -> None:
        details = self._config.api_config
        self._shared_connection = ZIConnection(details)
        self._shared_connection.connect()

    def connect_device(self, device: BaseInstrument) -> None:
        """Connects a device to the :class:`MultiDeviceConnection`.

        Adds a device to the :class:`MultiDeviceConnection` and connects the
        device to the shared Data Server. Depending on the device type, the
        device is added to respective dictionary and can then be accessed from
        there.

        Arguments:
            device (BaseInstrument): the device to be added to the
                MultiDeviceConnection, has to be one of :class:`HDAWG`,
                :class:`UHFQA`, :class:`UHFLI`, :class:`MFLI`, :class:`PQSC`

        Raises:
            ToolkitError: if the device is not recognized

        """
        if isinstance(device, HDAWG):
            self._hdawgs[device.name] = device
        elif isinstance(device, UHFQA):
            self._uhfqas[device.name] = device
        elif isinstance(device, PQSC):
            self._pqsc = device
        elif isinstance(device, UHFLI):
            self._uhflis = device
        elif isinstance(device, MFLI):
            self._mflis = device
        elif isinstance(device, SHFQA):
            self._shfqas[device.name] = device
        elif isinstance(device, SHFSG):
            self._shfsgs[device.name] = device
        else:
            _logger.error(
                "This device is not recognized!",
                _logger.ExceptionTypes.ToolkitError,
            )
        device.setup(connection=self._shared_connection)
        device.connect_device()

    @property
    def hdawgs(self):
        return self._hdawgs

    @property
    def uhfqas(self):
        return self._uhfqas

    @property
    def pqsc(self):
        return self._pqsc

    @property
    def uhflis(self):
        return self._uhflis

    @property
    def mflis(self):
        return self._mflis

    @property
    def shfqas(self):
        return self._shfqas

    @property
    def shfsgs(self):
        return self._shfsgs
