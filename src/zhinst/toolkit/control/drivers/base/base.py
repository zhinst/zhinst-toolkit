# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""Zurich Instruments Toolkit (zhinst-toolkit) Base Instrument Driver.

This driver provides a high-level controller for all Zurich Instrument
devices for Zurich Instruments Toolkit (zhinst-toolkit). It is based on
our Python API ziPython and forms the basis for instrument drivers used
in QCoDeS and Labber.
"""

from typing import Dict
import time
import zhinst.ziPython as zi

from zhinst.toolkit.control.connection import DeviceConnection, ZIConnection
from zhinst.toolkit.control.node_tree import NodeTree
from zhinst.toolkit.interface import InstrumentConfiguration, DeviceTypes, LoggerModule
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse

_logger = LoggerModule(__name__)


class BaseInstrument:
    """High-level controller for all Zurich Instrument devices.

    It can be used by itself or inherited for device specific
    controllers. It provides information and functionality common to
    all devices, such as a name, serial number, device type, interface,
    options, etc.

    The instrument holds a :class:`DeviceConnection` which handles all
    the communication with the data server. It also initializes a
    :class:`NodeTree` that is used to access all the settings in the
    device's nodetree.

        >>> import zhinst.toolkit as tk
        >>> ...
        >>> inst = tk.BaseInstrument("myDevice", tk.DeviceTypes.HDAWG, "dev8000", interface="USB")
        >>> inst.setup()
        Successfully connected to data server at localhost 8004 api version: 6
        >>> inst.connect_device()
        Successfully connected to device DEV8000 on interface USB
        >>> inst.nodetree
        <zhinst.toolkit.control.node_tree.NodeTree object at 0x000001640D222CC8>

    Arguments:
        name (str): Identifier for the instrument.
        device_type (:class:`DeviceType`): Type enum of the device type.
        serial (str): Serial number of the device, e.g. *'dev2281'*.
            The serial number can be found on instrument back panel.
        discovery: An instance of ziDiscovery to lookup the device

    Attributes:
        nodetree (:class:`zhinst.toolkit.control.node_tree.NodeTree`):
            A :class:`Nodetree` object contains a data structure that
            recreates the nodetree hierarchy of the instrument
            settings. The leaves of the tree are :class:`Parameters`
            that can be called to get and set the according value from
            the device. The :class:`Nodetree` can be used to navigate
            all available device settings without having to know the
            exact node path of the setting. Alternatively, the node can
            always be accessed using the `_set(...)` and `_get(...)`
            methods.
        name (str): Identifier for the instrument.
        device_type (:class:`DeviceType`): Type enum of the device type.
        serial (str): Serial number of the device.
        interface (str): Type of the device interface used, can be
            specified as a keyword argument to `__init__()`.
        options (list): Options installed on the instrument.
        is_connected (bool): A flag that shows if the device has
            established a connection to the data server.
    Raises:
        ToolkitError: If no serial serial is given or it is not of
            string type
    """

    def __init__(
        self, name: str, device_type: DeviceTypes, serial: str, discovery=None, **kwargs
    ) -> None:
        if not isinstance(serial, str):
            _logger.error(
                f"Serial must be a string", _logger.ExceptionTypes.ToolkitError
            )
        self._config = InstrumentConfiguration()
        self._config.instrument.name = name
        self._config.instrument.config.device_type = device_type
        self._config.instrument.config.serial = serial
        self._config.instrument.config.interface = kwargs.get("interface", "1GbE")
        self._config.api_config.host = kwargs.get("host", "localhost")
        self._config.api_config.port = kwargs.get("port", 8004)
        self._config.api_config.api = kwargs.get("api", 6)
        self._controller = DeviceConnection(
            self, discovery if discovery is not None else zi.ziDiscovery()
        )
        self._nodetree = None
        self._options = None

    def setup(self, connection: ZIConnection = None) -> None:
        """Sets up the data server connection.

        The details of the connection (`host`, `port`, `api_level`) can
        be specified as keyword arguments in the `__init__()` method.
        Alternatively, the user can pass an existing
        :class:`ZIConnection` to the data server to be used for the
        instrument.

        Arguments:
            connection (:class:`ZIConnection`): An existing data server
                connection. If specified, this data server will be used
                to establish a :class:`DeviceConnection`
                (default: None).

        """
        self._controller.setup(connection=connection)

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server.

        This method connects the device to the data server of its
        connection, initializes the :class:`NodeTree` and applies
        initial device settings. A data server connection needs to be
        set up beforehand by calling `setup()`.

        Arguments:
            nodetree (bool): If `True`,  the :class:`NodeTree` object
                will be initialized after connecting the device,
                otherwise not (Default: `True`).

        """
        self._controller.connect_device()
        if nodetree:
            self._nodetree = NodeTree(self)
        self._options = self._get("/features/options").split("\n")
        self._init_params()
        self._init_settings()

    def factory_reset(self, sync=True) -> None:
        """Load the factory default settings.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).
        """
        self._set(f"/system/preset/load", 1, sync=sync)
        _logger.info(f"Factory preset is loaded to device {self.serial.upper()}.")

    def _check_ref_clock(
        self, blocking: bool = True, timeout: int = 30, sleep_time: int = 1
    ) -> None:
        """Check if reference clock is locked successfully.

        Arguments:
            blocking (bool): A flag that specifies if the program should
                be blocked until the reference clock is 'locked'.
                (default: True)
            timeout (int): Maximum time in seconds the program waits
                when `blocking` is set to `True` (default: 30).
            sleep_time (int): Time in seconds to wait between
                requesting the reference clock status (default: 1)

        Raises:
            ToolkitError: If the device fails to lock on the reference
                clock.

        """
        start_time = time.time()
        while (
            blocking
            and start_time + timeout >= time.time()
            and self.ref_clock_status() != "locked"
        ):
            time.sleep(sleep_time)
        if (
            self.ref_clock_actual() != self.ref_clock()
            or self.ref_clock_status() != "locked"
        ):
            # Set the source to internal and throw an exception
            # if the clock is still not locked after timeout
            self.ref_clock("internal", sync=True)
            _logger.error(
                f"There was an error locking the device {self.name} ({self.serial}) "
                f"onto reference clock signal. Automatically switching to internal "
                f"reference clock. Please try again.",
                _logger.ExceptionTypes.ToolkitError,
            )
        else:
            _logger.info(
                f"Reference clock has been successfully locked to {self.ref_clock()} "
                f"on device {self.name} ({self.serial})."
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

    def _set(self, *args, sync=False):
        """Setter for the instrument.

        This method sets a node value to the device, specified by a
        node string. Passes the arguments to the setter of the
        :class:`DeviceConnection` and the :class:`ZIConnection`.

        The keyword argument *sync* is set to `False` by default and
        this method eventually wraps around `daq.set(...)` in
        :mod:`zhinst.ziPython`.

            >>> hdawg._set("sigouts/0/on", 1)

        If the keyword argument *sync* is set to `True`, this method
        eventually wraps around one of the three `daq.syncSet...(...)`
        methods in :mod:`zhinst.ziPython`.

            >>> hdawg._set("sigouts/0/on", 1, sync=True)
            1

        The method also supports wildcards in the node path that can be
        specified with ' * ' as a placeholder.

            >>> hdawg._set("sigouts/*/on", 1)

        Instead of specifying a single node path and a value, the user
        is free to pass a list of node / value pairs to the method to
        apply several settings at once with one call of the method.

            >>> settings = [
            >>>     ("sigouts/0/on", 1),
            >>>     ("sigouts/0/range", 0.75),
            >>>     ("sigouts/0/offset", 0.5),
            >>>     ("sigouts/0/filter", 0),
            >>>     ...
            >>> ]
            >>> hdawg._set(settings)

        If the keyword argument *sync* is set to `True` in this case, a
        global synchronisation between the device and the data server
        will be performed automatically using `daq.sync()` in
        :mod:`zhinst.ziPython`.

            >>> hdawg._set(settings, sync=True)

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after setting the node (default: False).

        Raises:
            ToolkitError: If called and the device in not yet connected
                to the data server.

        Returns:
            The value set on the device as returned from one of the
            API's `syncSet...(...)` methods, if a single node path and
            a value is passed and *sync* is set to `True`.

        """
        self._check_connected()
        return self._controller.set(*args, sync=sync)

    def _set_vector(self, *args):
        """Vector setter for the instrument.

        This method loads a vector to the device node, specified by a
        node string. Passes the arguments to the set_vector method of
        the :class:`DeviceConnection` and the :class:`ZIConnection`.
        Eventually this method wraps around `daq.setVector(...)` in
        :mod:`zhinst.ziPython`.

            >>> hdawg._set_vector("awgs/0/commandtable/data", command_table)

        The method also supports wildcards in the node path that can be
        specified with ' * ' as a placeholder.

            >>> hdawg._set_vector("awgs/*/commandtable/data", command_table)

        Instead of specifying a single node path and a vector, the user
        is free to pass a list of node / vector pairs to the method to
        apply several settings at once with one call of the method.

            >>> settings = [
            >>>     ("awgs/0/commandtable/data", command_table_0),
            >>>     ("awgs/1/commandtable/data", command_table_1),
            >>>     ("awgs/2/commandtable/data", command_table_2),
            >>>     ("awgs/3/commandtable/data", command_table_3),
            >>> ]
            >>> hdawg._set_vector(settings)

        Raises:
            ToolkitError: If called and the device in not yet connected
                to the data server.

        """
        self._check_connected()
        self._controller.set_vector(*args)

    def sync(self):
        """Perform a global synchronisation between the device and the
        data server.

        Eventually wraps around the daq.sync() of the API.

        Raises:
            ToolkitError: If called and the device in not yet connected
                to the data server.

        """
        self._check_connected()
        self._controller.sync()

    def _assert_node_value(
        self,
        *args,
        blocking: bool = True,
        timeout: float = 2,
        sleep_time: float = 0.005,
    ) -> bool:
        """Check if a node has the expected value.

        This method gets a node value of the device specified by a node
        string and check if it matches the expected value. Passes the
        arguments to the `_assert_node_value` of the
        :class:`DeviceConnection` and the :class:`ZIConnection`.

        Instead of specifying a single node path and a value, the user
        is free to pass a list of node / value pairs to the method to
        check several nodes at once with one call of the method.

        Arguments:
            blocking (bool): A flag that specifies if the program should
                be blocked until the node has the expected value
                (default: True).
            timeout (float): Maximum time in seconds the program waits
                when `blocking` is set to `True` (default: 2).
            sleep_time (float): Time in seconds to wait between
                requesting the node value (default: 0.005)

        Raises:
            ToolkitConnectionError: If called and the device in not yet
                connected to the data server.
            TypeError: If the number of arguments is invalid

        Returns:
            Either `True` or `False` to indicate whether the node does
            or does not have the expected value

        """
        pairs = []
        # Check how the node/value pairs are provided
        if len(args) == 2:
            # If just a single node/value pair is provided
            pairs = [(args[0], args[1])]
        elif len(args) == 1:
            # If a list of node/value tuples is provided
            pairs = args[0]
        else:
            _logger.error(
                "Invalid number of arguments!",
                _logger.ExceptionTypes.TypeError,
            )
        for i, pair in enumerate(pairs):
            start_time = time.time()
            while (
                blocking
                and start_time + timeout >= time.time()
                and self._get(pair[0]) != pair[1]
            ):
                time.sleep(sleep_time)
            # Check if the node still does not have the
            # expected value after timeout
            if self._get(pair[0]) != pair[1]:
                return False
        return True

    def _get(self, command: str, valueonly: bool = True):
        """Getter for the instrument.

        This method gets a node value from the device, specified by a
        node string. Passes the arguments to the getter of the
        :class:`DeviceConnection` and the :class:`ZIConnection`.
        Eventually this method wraps around `daq.get(...)` in
        :mod:`zhinst.ziPython`.

            >>> hdawg._get("sigouts/0/on")
            1

        The method also supports wildcards in the node path that can be
        specified with ' * ' as a placeholder. The flag `valueonly` can
        be used to get the exact node of the values.

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

        Arguments:
            valueonly (bool): A flag to select if only the value should be
                returned or a dict with node/value pairs (default: True)

        Raises:
            ToolkitError: if called and the device is not yet connected
                to the data server.

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
            ToolkitError: if called and the device is not yet connected
                to the data server.

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
            ToolkitError: if called and the device is not yet connected
                to the data server or the node does not exist.

        Returns:
            The dictionary that containing the keys: 'Node',
            'Description', 'Unit', etc.

        """
        # Add the device serial to the node string if it does not start
        # with '/zi/'.
        device_node = self._controller.command_to_node(node)
        self._check_node_exists(device_node)
        nested_dict = self._get_nodetree(device_node)
        inner_dict = list(nested_dict.values())[0]
        return inner_dict

    def _get_streamingnodes(self) -> Dict:
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
            ToolkitConnectionError: if the device is not connected to a data server.

        """
        if not self.is_connected:
            _logger.error(
                f"The device {self.name} ({self.serial}) is not connected to the data "
                f"server! Use device.connect_device() to connect the device to the "
                f"data server.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )

    def _check_node_exists(self, device_node: str):
        """Checks if the the specified node of the device exists.

        Raises:
            ToolkitError if the node does not exist.

        """
        if self._get_nodetree(device_node) == {}:
            _logger.error(
                f"The device {self.name} ({self.serial}) does not have "
                f"the node {device_node}. Please check the node address.",
                _logger.ExceptionTypes.ToolkitError,
            )

    @property
    def nodetree(self):
        return self._nodetree

    @property
    def name(self):
        return self._config.instrument.name

    @property
    def device_type(self):
        return self._config.instrument.config.device_type

    @property
    def serial(self):
        if self.is_connected:
            return self._controller.normalized_serial
        else:
            return self._config.instrument.config.serial

    @property
    def interface(self):
        return self._config.instrument.config.interface

    @property
    def options(self):
        return self._options

    @property
    def is_connected(self):
        return self._controller.is_connected
