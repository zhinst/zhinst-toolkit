# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.connection import DeviceConnection, ZIConnection
from zhinst.toolkit.control.nodetree import Nodetree
from zhinst.toolkit.interface import InstrumentConfiguration, DeviceTypes


class ZHTKException(Exception):
    pass


class BaseInstrument:
    """
    High-level controller common for all Zurich Instrument devices. Can be used 
    by itself or inherited for device specific controllers. Provides information 
    and functionality common to all devices, such as a name, an instrument 
    configuration (serial, interface, device type, ...).

    The instrument holds a DeviceConnection which handles all the communication 
    with the data server. It also initialize a Nodetree that is used to access 
    all the settings in the device's nodetree.

    Typical usage:
    
        import zhinst.toolkit as tk

        inst = tk.BaseInstrument("myDevice", "hdawg", "dev9999", interface="usb")
        inst.setup()
        inst.connect_device()

        inst.nodetree.sigouts[0].on(1)
        ...

    Args:
        name: Identifier for the instrument.
        device_type: Type of the device, i.e. must be in 
            {hdawg, uhfqa, uhfli, mfli, pqsc}
        serial: Serial number of the device, e.g. 'dev2281'. The serial number 
            can typically be found on the back panel.

    Attributes:
        nodetree (Nodetree): Nodetree object that contains the nodetree hirarchy 
            of the device settings. The leaves of the tree are parameters that can 
            be called to get and set the values.
        name (str)
        device_type (str)
        serial (str)
        interface (str)
        is_connected (bool)
    """

    def __init__(self, name: str, device_type: DeviceTypes, serial: str, **kwargs):
        self._config = InstrumentConfiguration()
        self._config._instrument._name = name
        self._config._instrument._config._device_type = device_type
        self._config._instrument._config._serial = serial
        self._config._instrument._config._interface = kwargs.get("interface", "1GbE")
        self._config._api_config.host = kwargs.get("host", "localhost")
        self._config._api_config.port = kwargs.get("port", 8004)
        self._config._api_config.api = kwargs.get("api", 6)
        self._controller = DeviceConnection(self)
        self._nodetree = None

    def setup(self, connection: ZIConnection = None):
        """
        Sets up the data server connection. The details of the connection 
        (host, port, api_level) can be specified as keyword arguments in the 
        __init__() method.
        Alternatively the user can pass an existing ZIConnection to the data 
        server to be used for the instrument.
        
        Args:
            connection (ZIConnection): defaults to None
        """
        self._controller.setup(connection=connection)

    def connect_device(self, nodetree=True):
        """
        Connects the device to the data server, initializes the nodetree and 
        performs initial device settings.
        
        Args:
            nodetree (bool): If True the nodetree object will be initialized 
                after connecting the device, otherwise not. Defaults to True.
        """
        self._check_connected()
        self._controller.connect_device()
        if nodetree:
            self._nodetree = Nodetree(self)
        self._options = self._get("/features/options").split("\n")
        self._init_settings()

    def _init_settings(self):
        """
        Initial device settings. Should be overridden by any instrument that 
        inherits from the BaseInstrument.
        """
        pass

    def _set(self, *args):
        """
        Setter for the instrument. Passes the arguments to the setter of the 
        DeviceConnection and the ZIConnection. Eventually wraps around 
        daq.set(...) in zhinst.ziPython.

        Raises ZHTKException if called and the device in not yet connected to 
        the data server.
        """
        self._check_connected()
        return self._controller.set(*args)

    def _get(self, command, valueonly=True):
        """
        Getter for the instrument. Passes the arguments to the getter of the 
        DeviceConnection and the ZIConnection. Eventually wraps around 
        daq.get(...) in zhinst.ziPython.
        
        Raises ZHTKException if called and the device in not yet connected to 
        the data server.
        """
        self._check_connected()
        return self._controller.get(command, valueonly=valueonly)

    def _get_nodetree(self, prefix, **kwargs):
        """
        Gets the entire nodetree from the instrument as a dictionary. Passes the 
        arguments to the DeviceConnection and the ZIConnection. Eventually wraps 
        around daq.listNodesJSON(...) in zhinst.ziPython.
        
        Raises ZHTKException if called and the device in not yet connected to 
        the data server.
        """
        self._check_connected()
        return self._controller.get_nodetree(prefix, **kwargs)

    def _get_streamingnodes(self):
        self._check_connected()
        nodes = self._controller.get_nodetree(f"/{self.serial}/*", streamingonly=True)
        nodes = list(nodes.keys())
        streaming_nodes = {}
        for node in nodes:
            node = node.lower()
            node_split = node.split("/")[2:]
            node_name = node_split[0][:-1] + node_split[1]
            if "pid" in node_name:
                node_name += f"_{node_split[-1]}"
            streaming_nodes[node_name] = node.replace(f"/{self.serial}", "")
        return streaming_nodes

    def _check_connected(self):
        """
        Check if the device is connected to the data server, otherwise raises 
        a ZHTKException.
        """
        if not self.is_connected:
            raise ZHTKException(
                f"The device {self.name} ({self.serial}) is not connected to a Data Server! Use device.setup() to establish a data server connection."
            )

    @property
    def nodetree(self):
        return self._nodetree

    @property
    def name(self):
        return self._config._instrument._name

    @property
    def device_type(self):
        return self._config._instrument._config._device_type

    @property
    def serial(self):
        return self._config._instrument._config._serial

    @property
    def interface(self):
        return self._config._instrument._config._interface

    @property
    def options(self):
        return self._options

    @property
    def is_connected(self):
        return not self._controller._connection is None
