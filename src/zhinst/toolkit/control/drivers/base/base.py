# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
from typing import List, Dict
import logging
import time

import zhinst.ziPython as zi
from zhinst.toolkit.control.connection import DeviceConnection, ZIConnection
from zhinst.toolkit.control.node_tree import NodeTree
from zhinst.toolkit.interface import InstrumentConfiguration, DeviceTypes
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse


_logger = logging.getLogger(__name__)


class ToolkitError(Exception):
    pass


class BaseInstrument:
    """High-level controller for all Zurich Instrument devices.

    It can be used by itself or inherited for device specific controllers. It
    provides information and functionality common to all devices, such as a
    name, serial number, device type, interface, etc.

    The instrument holds a :class:`DeviceConnection` which handles all the
    communication with the data server. It also initializes a :class:`NodeTree`
    that is used to access all the settings in the device's nodetree.

        >>> import zhinst.toolkit as tk
        >>> ...
        >>> inst = tk.BaseInstrument("myDevice", tk.DeviceTypes.HDAWG, "dev9999", interface="USB")
        >>> inst.setup()
        Successfully connected to data server at localhost 8004 api version: 6
        >>> inst.connect_device()
        Successfully connected to device DEV9999 on interface USB
        >>> inst.nodetree
        >>> ...

    Arguments:
        name (str): Identifier for the instrument.
        device_type (:class:`DeviceType`): Type enum of the device type.
        serial (str): Serial number of the device, e.g. *'dev2281'*. The serial
            number can be found on instrument back panel.
        discovery: An instance of ziDiscovery to lookup the device

    Attributes:
        nodetree (:class:`zhinst.toolkit.control.node_tree.NodeTree`): A
            :class:`Nodetree` object contains a data structure that recreates
            the nodetree hierarchy of the instrument settings. The leaves of the
            tree are :class:`Parameters` that can be called to get and set the
            according value from the device. The :class:`Nodetree` can be used
            to navigate all available device settings without having to know the
            exact node path of the setting. Alternatively, the node can always
            be accessed using the `_set(...)` and `_get(...)` methods.
        name (str): Identifier for the instrument.
        device_type (:class:`DeviceType`): Type enum of the device type.
        serial (str): Serial number of the device.
        interface (str): Type of the device interface used, can be specified as
            a keyword argument to `__init__()`.
        is_connected (bool): A flag that shows if the device has established a
            connection to the data server.
    Raises:
        ToolkitError: If no serial serial is given
    """

    def __init__(
        self, name: str, device_type: DeviceTypes, serial: str, discovery=None, **kwargs
    ) -> None:
        if not isinstance(serial, str):
            raise ToolkitError(f"Serial must be a string")

        self._config = InstrumentConfiguration()
        self._config._instrument._name = name
        self._config._instrument._config._device_type = device_type
        self._config._instrument._config._serial = serial
        self._config._instrument._config._interface = kwargs.get("interface", "1GbE")
        self._config._api_config.host = kwargs.get("host", "localhost")
        self._config._api_config.port = kwargs.get("port", 8004)
        self._config._api_config.api = kwargs.get("api", 6)
        self._controller = DeviceConnection(
            self, discovery if discovery is not None else zi.ziDiscovery()
        )
        self._nodetree = None
        self._options = None
        self._normalized_serial = None

    def setup(self, connection: ZIConnection = None) -> None:
        """Sets up the data server connection.

        The details of the connection (`host`, `port`, `api_level`) can be
        specified as keyword arguments in the `__init__()` method. Alternatively
        the user can pass an existing :class:`ZIConnection` to the data server
        to be used for the instrument.

        Arguments:
            connection (:class:`ZIConnection`): An existing data server
                connection. If specified, this data server will be used to
                establish a :class:`DeviceConnection`. (default: None)

        """
        self._controller.setup(connection=connection)

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server.

        This method connects the device to the data server of its connection,
        initializes the :class:`NodeTree` and applies initial device settings.
        A data server connection needs to be set up beforehand by calling
        `setup()`.

        Arguments:
            nodetree (bool): If `True`,  the :class:`NodeTree` object will be
                initialized after connecting the device, otherwise not.
                (Default: `True`)

        """
        self._check_connected()
        self._controller.connect_device()

        if nodetree:
            self._nodetree = NodeTree(self)
        self._options = self._get("/features/options").split("\n")
        self._init_params()
        self._init_settings()

    def factory_reset(self) -> None:
        """Loads the factory default settings."""
        self._set(f"/system/preset/load", 1)
        _logger.info(f"Factory preset is loaded to device {self.serial.upper()}.")

    def _check_ref_clock(self, blocking=True, timeout=30) -> None:
        """Check if reference clock is locked succesfully.

        Keyword Arguments:
            blocking (bool): A flag that specifies if the program should
                be blocked until the reference clock is 'locked'.
                (default: True)
            timeout (int): Maximum time in seconds the program waits
                when `blocking` is set to `True`. (default: 30)

        """
        ref_clock_set = self.ref_clock()
        ref_clock_status = self.ref_clock_status()
        start_time = time.time()
        while (
            blocking
            and start_time + timeout >= time.time()
            and ref_clock_status != "locked"
        ):
            time.sleep(1)
            # Check again if status is 'locked' and update the variable.
            ref_clock_status = self.ref_clock_status()
        # Throw an exception if the clock is still not locked after timeout
        ref_clock_actual = self.ref_clock_actual()
        if ref_clock_actual != ref_clock_set:
            raise Exception(
                f"There was an error locking the device {self.name} ({self.serial}) "
                f"onto reference clock signal. Please try again."
            )
        else:
            _logger.info(
                f"Reference clock has been succesfully locked on the "
                f"device {self.name} ({self.serial})."
            )

    def _init_params(self):
        """Initialize parameters associated with device nodes.

        Can be overwritten by any instrument that inherits from the
        :class:`BaseInstrument`.

        """
        self.data_server_version = Parameter(
            self,
            self._get_node_dict(f"/zi/about/revision"),
            device=self,
            get_parser=Parse.version_parser,
        )
        self.firmware_version = Parameter(
            self,
            self._get_node_dict(f"/system/fwrevision"),
            device=self,
        )
        self.fpga_version = Parameter(
            self,
            self._get_node_dict(f"/system/fpgarevision"),
            device=self,
        )

    def _init_settings(self):
        """Initial device settings.

        Can be overwritten by any instrument that inherits from the
        :class:`BaseInstrument`.

        """
        pass

    def _set(self, *args):
        """Setter for the instrument.

        This method sets a node value from the device, specified by a node
        string. Passes the arguments to the setter of the
        :class:`DeviceConnection` and the :class:`ZIConnection`. Eventually
        this method wraps around `daq.set(...)` in :mod:`zhinst.ziPython`.

            >>> hdawg._set("sigouts/0/on", 1)

        The method also supports wildcards in the node path that can be
        specified with ' * ' as a placeholder.

            >>> hdawg._set("sigouts/*/on", 1)

        Instead of specifying a single node path and a value, the user is free
        to pass a list of node / value pairs to the method to apply several
        settings at once with one call of the method.

            >>> settings = [
            >>>     ("sigouts/0/on", 1),
            >>>     ("sigouts/0/range", 0.75),
            >>>     ("sigouts/0/offset", 0.5),
            >>>     ("sigouts/0/filter", 0),
            >>>     ...
            >>> ]
            >>> hdawg._set(settings)

        Raises:
            ToolkitError: If called and the device in not yet connected to the
                data server.

        Returns:
            The value set on the device as returned from the API's `set(...)`
            method.

        """
        self._check_connected()
        return self._controller.set(*args)

    def _setVector(self, *args):
        """Vector setter for the instrument.

        This method loads a vector to the device node, specified by a
        node string. Passes the arguments to the setVector method of the
        :class:`DeviceConnection` and the :class:`ZIConnection`.
        Eventually this method wraps around `daq.setVector(...)` in
        :mod:`zhinst.ziPython`.

            >>> hdawg._setVector("awgs/0/commandtable/data", command_table)

        The method also supports wildcards in the node path that can be
        specified with ' * ' as a placeholder.

            >>> hdawg._setVector("awgs/*/commandtable/data", command_table)

        Instead of specifying a single node path and a vector, the user
        is free to pass a list of node / vector pairs to the method to
        apply several settings at once with one call of the method.

            >>> settings = [
            >>>     ("awgs/0/commandtable/data", command_table_0),
            >>>     ("awgs/1/commandtable/data", command_table_1),
            >>>     ("awgs/2/commandtable/data", command_table_2),
            >>>     ("awgs/3/commandtable/data", command_table_3),
            >>> ]
            >>> hdawg._setVector(settings)

        Raises:
            ToolkitError: If called and the device in not yet connected
                to the data server.

        """
        self._check_connected()
        self._controller.setVector(*args)

    def _get(self, command: str, valueonly: bool = True):
        """Getter for the instrument.

        This method gets a node value from the device, specified by a node
        string. Passes the arguments to the getter of the
        :class:`DeviceConnection` and the :class:`ZIConnection`. Eventually this
        method wraps around `daq.get(...)` in :mod:`zhinst.ziPython`.

            >>> hdawg._get("sigouts/0/on")
            1

        The method also supports wildcards in the node path that can be
        specified with ' * ' as a placeholder. The flag `valueonly` can be used to
        get the exact node of the values.

            >>> hdawg._get("sigouts/*/on")
            [1, 0, 0, 0, 0, 0, 0]
            >>> hdawg._get("sigouts/*/on", valueonly=False)
            {'sigouts/0/on': 1,
             'sigouts/1/on': 0,
             'sigouts/2/on': 0,
             'sigouts/3/on': 0,
             'sigouts/4/on': 0,
             'sigouts/5/on': 0,
             'sigouts/6/on': 0,
             'sigouts/7/on': 0}

        Arguments:
            command (str): A node string to the parameter.

        Keyword Arguments:
            valueonly (bool): A flag to select if only the value should be
                returned or a dict with node/value pairs (default: True)

        Raises:
            ToolkitError: if called and the device is not yet connected to
                the data server.

        Returns:
            The value of the parameter corresponding to the specified node.
            If `valueonly=False` the value is returned in a dict with the
            node as a key.

        """
        self._check_connected()
        return self._controller.get(command, valueonly=valueonly)

    def _get_nodetree(self, prefix: str, **kwargs) -> Dict:
        """Gets the entire nodetree from the instrument as a dictionary.

        This method passes the arguments to the :class:`DeviceConnection` and
        the :class:`ZIConnection`. Eventually this method wraps around
        `daq.listNodesJSON(...)` in :mod:`zhinst.ziPython`.

        Arguments:
            prefix (str): A string that is passed to `listNodesJSON(...)` to
                specify the subtree for which the nodes should be returned.

        Raises:
            ToolkitError: if called and the device is not yet connected to
                the data server.

        Returns:
            The dictionary that is returned from the API's `listNodesJSON(...)`
            method.

        """
        self._check_connected()
        return self._controller.get_nodetree(prefix, **kwargs)

    def _get_node_dict(self, node: str) -> Dict:
        """Gets the dictionary associated with the specified node.

        This method uses `_get_nodetree()` to retrieve the nested
        dictionary associated with the specified node of the device.
        Then it extracts the value of the outer dictionary to return the
        inner dictionary containing the keys: 'Node', 'Description',
        'Unit', etc.

        Arguments:
            node (str): A string that specifies the node address.

        Raises:
            ToolkitError: if called and the device is not yet connected to
                the data server or the node does not exist.

        Returns:
            The dictionary that containing the keys: 'Node',
        'Description', 'Unit', etc.

        """
        # Add the device serial to the node string if it does not start
        # with '/zi/'.
        device_node = self._controller._command_to_node(node)
        self._check_node_exists(device_node)
        nested_dict = self._get_nodetree(device_node)
        inner_dict = list(nested_dict.values())[0]
        return inner_dict

    def _get_streamingnodes(self) -> List:
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
        """Checks if the device is connected to the data server.

        Raises:
            ToolkitError if the device is not connected to a data server.

        """
        if not self.is_connected:
            raise ToolkitError(
                f"The device {self.name} ({self.serial}) is not connected to a Data Server! Use device.setup() to establish a data server connection."
            )

    def _check_node_exists(self, device_node: str):
        """Checks if the the specified node of the device exists.

        Raises:
            ToolkitError if the node does not exist.

        """
        if self._get_nodetree(device_node) == {}:
            raise ToolkitError(
                f"The device {self.name} ({self.serial}) does not have "
                f"the node {device_node}. Please check the node address."
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
        if self._controller.normalized_serial is not None:
            return self._controller.normalized_serial
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
