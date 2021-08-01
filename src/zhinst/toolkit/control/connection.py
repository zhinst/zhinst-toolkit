# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import json

from zhinst.toolkit.control.parsers import Parse
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
import zhinst.ziPython as zi

_logger = LoggerModule(__name__)


class ZIConnection:
    """Connection to a Zurich Instruments data server object.

    Wraps around the basic functionality of connecting to the
    data server, connecting a device to the server, and setting and
    getting node values. It also holds an awg module object that
    implements the `daq.awgModule` module as well as DAQ module and
    Sweeper Module connections.

    Arguments:
        connection_details: Part of the instrument config.

    Attributes:
        connection_details (ZIAPI)
        daq (zi.ziDAQServer): data server object from zhinst.ziPython

    Properties:
        established (bool): A flag showing if a connection has been
            established.
        awg_module (AWGModuleConnection)
        daq_module (DAQModuleConnection)
        sweeper_module (SweeperModuleConnection)

    """

    def __init__(self, connection_details):
        self._connection_details = connection_details
        self._daq = None
        self._awg_module = None
        self._scope_module = None
        self._daq_module = None
        self._sweeper_module = None
        self._device_type = None

    def connect(self):
        """Established a connection to the data server.

        Uses the connection details (host, port, api level) specified in the
        'connection_details' to open a `zi.ziDAQServer` data server object that
        is used for all communication to the data server.

        Raises:
            ToolkitConnectionError: If connection to the Data Server
                could not be established

        """
        try:
            self._daq = zi.ziDAQServer(
                self._connection_details.host,
                self._connection_details.port,
                self._connection_details.api,
            )
        except RuntimeError:
            _logger.error(
                f"No connection could be established with the connection details: "
                f"{self._connection_details}",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if self._daq is not None:
            print(
                f"Successfully connected to data server at "
                f"{self._connection_details.host}:"
                f"{self._connection_details.port} "
                f"api version: {self._connection_details.api}"
            )
            self._awg_module = AWGModuleConnection(self._daq)
            self._scope_module = ScopeModuleConnection(self._daq)
            self._daq_module = DAQModuleConnection(self._daq)
            self._sweeper_module = SweeperModuleConnection(self._daq)
        else:
            _logger.error(
                f"No connection could be established with the connection details: "
                f"{self._connection_details}",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )

    @property
    def established(self):
        return self._daq is not None

    def connect_device(self, serial=None, interface=None):
        """Connects a device to the data server.

        Arguments:
            serial (str): the serial number of the device, e.g. 'dev8030'
            interface (str): the type of interface, must be either '1gbe' or
                'usb'

        Raises:
            ToolkitConnectionError: If the connection could not be
                established.

        """
        if self._daq is None:
            _logger.error(
                "No existing connection to data server",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if any(k is None for k in [serial, interface]):
            _logger.error(
                "To connect a Zurich Instruments' device, you need a serial and an "
                "interface [1gbe or usb]",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        self._daq.connectDevice(serial, interface)
        print(
            f"Successfully connected to device {serial.upper()} "
            f"on interface {interface.upper()}"
        )
        # Update device type
        self._device_type = self._daq.getString(f"/{serial}/features/devtype")
        # Check if device has AWG functionality and update the AWG module
        device_awg_nodes = self._daq.listNodes(f"{serial}/awgs")
        if device_awg_nodes:
            self._awg_module.update(device=serial, index=0)
        # Check if the device has Scope functionality
        device_scope_nodes = self._daq.listNodes(f"{serial}/scope")
        if device_scope_nodes:
            # Check if device is UHF or MF and update the scope module
            if self._device_type.startswith(("UHF", "MF")):
                self._scope_module.update_device(device=serial)

    def set(self, *args):
        """Wrapper around the `zi.ziDAQServer.set()` method of the API.

        Passes all arguments to the underlying method.

        Raises:
            ToolkitConnectionError: If the connection is not yet
                established

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        self._daq.set(*args)

    def sync_set(self, *args):
        """Call one of the three `zi.ziDAQServer.syncSet...(...)` commands

        Depending on the passed argument, this method should call one
        of `zi.ziDAQServer.syncSetInt()`, `zi.ziDAQServer.syncSetDouble()`
        or `zi.ziDAQServer.syncSetString()`

        Raises:
            ToolkitConnectionError: If the connection is not yet
                established

        Returns:
            The value returned from `daq.syncSet...()`

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if isinstance(args[1], int):
            return self._daq.syncSetInt(*args)
        elif isinstance(args[1], float):
            return self._daq.syncSetDouble(*args)
        elif isinstance(args[1], str):
            return self._daq.syncSetString(*args)

    def set_vector(self, *args):
        """Wrapper around the `zi.ziDAQServer.setVector()` method of the API.

        Passes all arguments to the underlying method.

        Raises:
            ToolkitConnectionError: If the connection is not yet
                established

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        for setting in args[0]:
            self._daq.setVector(setting[0], setting[1])

    def sync(self):
        """Wrapper around the `zi.ziDAQServer.sync()` method of the API.

        Raises:
            ToolkitConnectionError: If the connection is not yet
                established

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        self._daq.sync()

    def get(self, *args, **kwargs):
        """Wrapper around the `zi.ziDAQServer.get(...)` method of the API.

        Passes all arguments and keyword arguments to the underlying method.

        Raises:
            ToolkitConnectionError: If the connection is not yet
                established

        Returns:
            the value returned from `daq.get(...)`

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return self._daq.get(*args, **kwargs)

    def get_sample(self, *args, **kwargs):
        """Wrapper around the `daq.getSample(...)` method of the API.

        Passes all arguments and keyword arguments to the underlying method.
        Used only for certain streaming nodes on the UHFLI or MFLI devices.

        Raises:
            ToolkitConnectionError: Is the connection is not yet
                established

        Returns:
            the value returned from `daq.getSample(...)`

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return self._daq.getSample(*args, **kwargs)

    def list_nodes(self, *args, **kwargs):
        """Wrapper around the `daq.listNodesJSON(...)` method of the API.

        Passes all arguments and keyword arguments to the underlying
        method.

        Raises:
            ToolkitConnectionError: If the connection is not yet
                established

        Returns:
            the value returned from `daq.listNodesJSON(...)`

        """
        if not self.established:
            _logger.error(
                "The connection is not yet established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return self._daq.listNodesJSON(*args, **kwargs)

    @property
    def daq(self):
        if self._daq is None:
            _logger.error(
                "No existing connection to data server",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        else:
            return self._daq

    @property
    def awg_module(self):
        return self._awg_module

    @property
    def scope_module(self):
        return self._scope_module

    @property
    def daq_module(self):
        return self._daq_module

    @property
    def sweeper_module(self):
        return self._sweeper_module


class AWGModuleConnection:
    """Connection to an AWG Module.

    Implements an awg module as `daq.awgModule(...)` of the API with
    get and set methods of the module. Allows to address different awgs on
    different devices with the same awg module using the `update(...)` method.
    Also wraps around all other methods from the API.

    Arguments:
        daq (zi.ziDAQServer)

    Properties:
        index (int): index of the AWG
        device (str): serial number of the device

    """

    def __init__(self, daq):
        self._awgModule = daq.awgModule()
        self._awgModule.execute()
        self._device = self._awgModule.getString("/device")
        self._index = self._awgModule.getInt("/index")

    def set(self, *args, **kwargs):
        self.update(**kwargs)
        self._awgModule.set(*args)

    def get(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.get(*args, flat=True)

    def get_int(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.getInt(*args)

    def get_double(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.getDouble(*args)

    def get_string(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.getString(*args)

    def update(self, **kwargs):
        if "device" in kwargs.keys():
            self._update_device(kwargs["device"])
        if "index" in kwargs.keys():
            self._update_index(kwargs["index"])

    def _update_device(self, device):
        if device != self.device:
            self._update_index(0)
            self._awgModule.set("/device", device)
            self._device = device

    def _update_index(self, index):
        if index != self.index:
            self._awgModule.set("/index", index)
            self._index = index

    @property
    def index(self):
        return self._index

    @property
    def device(self):
        return self._device


class ScopeModuleConnection:
    """Connection to a Scope Module.

    Implements a Scope module as `daq.scopeModule(...)` of the API with
    get and set methods of the module. Also wraps around all other
    methods from the API.

    Arguments:
        daq (zi.ziDAQServer)

    """

    def __init__(self, daq):
        self._scopeModule = daq.scopeModule()
        self._device = None

    def execute(self):
        # Tell the module to be ready to acquire data;
        # reset the module's progress to 0.0.
        self._scopeModule.execute()

    def set(self, *args):
        self._scopeModule.set(*args)

    def subscribe(self, device):
        # Subscribe to the scope's data in the module.
        wave_nodepath = f"/{device}/scopes/0/wave"
        self._scopeModule.subscribe(wave_nodepath)

    def progress(self):
        return self._scopeModule.progress()[0]

    def records(self):
        return self._scopeModule.getInt("records")

    def historylength(self, length=None):
        if length is None:
            return self._scopeModule.getInt("historylength")
        else:
            self._scopeModule.set("historylength", length)

    def averager_weight(self, weight=None):
        if weight is None:
            return self._scopeModule.getInt("averager/weight")
        else:
            self._scopeModule.set("averager/weight", weight)

    def mode(self, mode=None):
        if mode is None:
            v = self._scopeModule.getInt("mode")
            return Parse.get_scope_mode(v)
        else:
            v = Parse.set_scope_mode(mode)
            self._scopeModule.set("mode", v)

    def finish(self):
        self._scopeModule.finish()

    def read(self):
        return self._scopeModule.read(True)

    def update_device(self, device):
        if device != self.device:
            self.subscribe(device)
            self._device = device

    @property
    def device(self):
        return self._device


class DAQModuleConnection:
    """Connection to a DAQ Module.

    Implements a daq module as `daq.DataAcquisitionModule(...)` of the API with
    get and set methods of the module. Also wraps around all other methods from
    the API.

    Arguments:
        daq (zi.ziDAQServer)

    Properties:
        device (str): serial number of the device

    """

    def __init__(self, daq):
        self._module = daq.dataAcquisitionModule()
        self._device = self._module.getString("/device")

    def execute(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.execute()

    def finish(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.finish()

    def finished(self, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.finished()

    def progress(self, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.progress()

    def trigger(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.trigger()

    def read(self, device=None, **kwargs):
        if device is not None:
            self.update_device(device)
        return self._module.read(**kwargs)

    def subscribe(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.subscribe(*args)

    def unsubscribe(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.unsubscribe(*args)

    def save(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.save(*args)

    def clear(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.clear()

    def set(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.set(*args)

    def get(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.get(*args, flat=True)

    def get_int(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.getInt(*args)

    def get_double(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.getDouble(*args)

    def get_string(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.getString(*args)

    def get_nodetree(self, prefix, device=None, **kwargs):
        if device is not None:
            self.update_device(device)
        tree = json.loads(self._module.listNodesJSON(prefix, **kwargs))
        return tree

    def update_device(self, device):
        if device != self.device:
            self._module.set("/device", device)
            self._device = device

    @property
    def device(self):
        return self._device


class SweeperModuleConnection(DAQModuleConnection):
    """Connection to a Sweeper Module.

    Inherits from `DAQModuleConnection` but uses the `daq.sweep()`
    module instead.

    """

    def __init__(self, daq):
        self._module = daq.sweep()
        self._device = self._module.getString("/device")


class DeviceConnection(object):
    """Implements a connection to the data server for a single device.

    Wraps around the data server connection (ZIConnection) for a single device
    with a specified serial number and type. This class allows it to call
    get(...) and set(...) for any node in the nodetree without having to specify
    the device address. In contrast to zhinst.ziPython the get(...) method
    returns only the value of the node as a scalar or numpy array.

    Arguments:
        device (BaseInstrument): Associated device that the device connection
            is used for.
        discovery: an instance of ziDiscovery

    Attributes:
        connection (ZIConnection): Data server connection (common for more
            than one instrument).
        device (BaseInstrument): Associated instrument that is addressed.
        normalized_serial (str): Serial number of the device written in
            lowercase.
        discovery (ziDiscovery): The ziDiscovery instant passed as
            argument
        is_established (bool): A flag that shows if a connection to the
            data server is established.
        is_connected (bool): A flag that shows if the instrument is
            connected to the data server.

    """

    def __init__(self, device, discovery):
        self._connection = None
        self._device = device
        self._normalized_serial = None
        self._discovery = discovery
        self._is_established = False
        self._is_connected = False

    def setup(self, connection: ZIConnection = None):
        """Establishes the connection to the data server.

        Arguments:
            connection (ZIConnection): An existing connection can be passed as
                an argument. (default: None)

        Raises:
            ToolkitConnectionError: If connection to the Data Server
                could not be established

        """
        if connection is None:
            details = self._device._config._api_config
            self._connection = ZIConnection(details)
        else:
            self._connection = connection
        if not self._connection.established:
            self._connection.connect()
        self._is_established = True

    def _normalize_serial(self, serial):
        try:
            device_props = self._discovery.get(self._discovery.find(serial))
            discovered_serial = device_props["deviceid"]
            return discovered_serial.lower()
        except RuntimeError:
            _logger.error(
                f"Failed to discover a device with serial {serial}",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )

    def connect_device(self):
        """Connects the device to the data server.

        Raises:
            ToolkitConnectionError: If connection to the Data Server
                could not be established

        """
        # First, check if a connection to the data server is established
        if not self._is_established:
            _logger.error(
                "Connection to the data server is not established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if self._discovery is not None:
            self._normalized_serial = self._normalize_serial(self._device.serial)
        else:
            self._normalized_serial = self._device.serial
        self._connection.connect_device(
            serial=self._normalized_serial,
            interface=self._device.interface,
        )
        self._is_connected = True

    def set(self, *args, sync=False):
        """Sets the value of the node for the connected device.

        Parses the input arguments to either set a single node/value
        pair or a list of node/value tuples.

        If a single node path and a value is specified and the keyword
        argument *sync* is set to `False`, this method eventually wraps
        around `daq.set(...)` in :mod:`zhinst.ziPython`. If the keyword
        argument *sync* is set to `True`, this method wraps around one
        of the three `daq.syncSet...(...)` methods in
        :mod:`zhinst.ziPython`.

        If a list of node / value pairs is passed to the method to
        apply several settings at once and the keyword argument *sync*
        is set to `True`, a global synchronisation between the device
        and the data server will be performed automatically using
        `daq.sync()` in :mod:`zhinst.ziPython`.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after setting the node (default: False).

        Raises:
            TypeError: If the input arguments are invalid.
            ToolkitConnectionError: If the device is not connected to
                the Data Server

        Returns:
            The value set on the device as returned from one of the
            API's `syncSet...(...)` methods, if a single node path and
            a value is passed and *sync* is set to `True`.

        """
        # If just a single node/value pair is provided
        if len(args) == 2:
            settings = self._commands_to_node([(args[0], args[1])])
            # Check if synchronisation is enabled
            if sync:
                # Return the value returned by API
                return self._connection.sync_set(*settings[0])
            else:
                self._connection.set(settings)
        # If a list of node/value tuples is provided
        elif len(args) == 1:
            settings = self._commands_to_node(args[0])
            self._connection.set(settings)
            if sync:
                self.sync()
        else:
            _logger.error(
                "Invalid number of arguments!",
                _logger.ExceptionTypes.TypeError,
            )

    def set_vector(self, *args):
        """Sets the vector value of the node for the connected device.

        Parses the input arguments to either set a single node/vector
        pair or a list of node/vector tuples. Eventually wraps around
        the daq.setVector(...) of the API.

        Raises:
            TypeError: If is the input arguments are invalid.
            ToolkitConnectionError: If the device is not connected to
                the Data Server

        """
        settings = []
        if len(args) == 2:
            settings = [(args[0], args[1])]
        elif len(args) == 1:
            settings = args[0]
        else:
            _logger.error(
                "Invalid number of arguments!",
                _logger.ExceptionTypes.TypeError,
            )
        settings = self._commands_to_node(settings)
        self._connection.set_vector(settings)

    def sync(self):
        """Perform a global synchronisation between the device and the
        data server.

        Eventually wraps around the daq.sync() of the API.

        Raises:
            ToolkitConnectionError: If the connection to the data
                server is not established

        """
        self._connection.sync()

    def get(self, command, valueonly=True):
        """Gets the value of the node for the connected device.

        Parses the returned dictionary from the data server to output
        only the actual value in a nice format. Wraps around the
        daq.get(...) of the API.

        Multiple nodes can be specified as a list

        Arguments:
            command (str): node string of the value to get
            valueonly (bool): a flag specifying if the entire dict
                should be returned as from the API or only the actual
                value (default: True)

        Raises:
            ToolkitConnectionError: If no device is connected
            TypeError: If the passed argument is not a string or list

        Returns:
            The value of the node.

        """
        node_string = ""
        if self._device is not None:
            if isinstance(command, list):
                paths = []
                for c in command:
                    paths.append(self.command_to_node(c))
                node_string = ", ".join([p for p in paths])
            elif isinstance(command, str):
                node_string = self.command_to_node(command)
            else:
                _logger.error(
                    "Invalid argument! It must be either a node path string or "
                    "list of node path strings",
                    _logger.ExceptionTypes.TypeError,
                )
            if (
                self._device.device_type in [DeviceTypes.UHFLI, DeviceTypes.MFLI]
                and "sample" in command.lower()
            ):
                data = self._connection.get_sample(node_string)
                return DeviceConnection._get_value_from_streamingnode(data)
            else:
                data = self._connection.get(node_string, settingsonly=False, flat=True)
            data = self._get_value_from_dict(data)
            if valueonly:
                if len(data) > 1:
                    return [v for v in data.values()]
                else:
                    return list(data.values())[0]
            else:
                return data
        else:
            _logger.error(
                "No device connected!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )

    def get_nodetree(self, prefix: str, **kwargs):
        """Gets the entire nodetree of the connected device.

        Wraps around the `daq.listNodesJSON(...)` method in zhinst.ziPython.

        Arguments:
            prefix (str): a partial node string that is passed to
                'listNodesJSON(...)' to specify which part of the nodetree
                to return

        Raises:
            ToolkitConnectionError: If the connection to the data
                server is not established

        Returns:
            The nodetree of the device as a dictionary returned from the API.

        """
        return json.loads(self._connection.list_nodes(prefix, **kwargs))

    def _get_value_from_dict(self, data):
        """Retrieves the parameter value from the returned dict of the API.

        Parses the dict returned from the Python API into a nicer format.
        Removes the device serial from the node string to be used as a key in
        the returned dict. The corresponding value is the returned value from
        the Python API, can be a scalar or vector.

        Arguments:
            data (dict): A dictionary as returned from the Python API.

        Raises:
            ToolkitConnectionError: if no data is returned from the API

        Returns:
            A dictionary with node/value as key and value.

        """
        if not isinstance(data, dict):
            _logger.error(
                "Something went wrong...",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if not len(data):
            _logger.error(
                "No data returned... does the node exist?",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace(f"/{self._normalized_serial}/", "")
            if isinstance(data_dict, list):
                data_dict = data_dict[0]
            if "value" in data_dict.keys():
                new_data[key] = data_dict["value"][0]
            if "vector" in data_dict.keys():
                new_data[key] = data_dict["vector"]
        return new_data

    @staticmethod
    def _get_value_from_streamingnode(data):
        """Gets the (complex) data only for specific demod sample nodes.

        Arguments:
            data (dict): A dictionary as returned from the Python API.

        Raises:
            ToolkitConnectionError: if no data is returned from the API

        Returns:
            The complex demod sample value.

        """
        if not isinstance(data, dict):
            _logger.error(
                "Something went wrong...",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if not len(data):
            _logger.error(
                "No data returned... does the node exist?",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        if "x" not in data.keys() or "y" not in data.keys():
            _logger.error(
                "No 'x' or 'y' in streaming node data!",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return data["x"][0] + 1j * data["y"][0]

    def _commands_to_node(self, settings):
        """Converts a list of command strings to a list of node paths.

        Parses a list of command and value pairs into a a list of node value
        pairs that can be passed to 'ziDAQServer.set(...)'. E.g. adds the
        device serial in front of every command.

        Arguments:
            settings (list): list of command/value pairs

        Raises:
            TypeError: if the command/value pairs are not specified as
                pairs/tuples
            ToolkitConnectionError: If the device is not connected to
                the Data Server

        Returns:
            The parsed list.

        """
        new_settings = []
        for args in settings:
            try:
                if len(args) != 2:
                    _logger.error(
                        "node/value must be specified as pairs!",
                        _logger.ExceptionTypes.TypeError,
                    )
            except TypeError:
                _logger.error(
                    "node/value must be specified as pairs!",
                    _logger.ExceptionTypes.TypeError,
                )
            new_settings.append((self.command_to_node(args[0]), args[1]))
        return new_settings

    def command_to_node(self, command):
        """Converts a command string to a node path.

        Parses a single command into a node string that can be passed
        to `ziDAQServer.set(...)`. Checks if the command starts with a '/' and
        adds the right device serial if the command
        does not start with '/zi/'.

        Arguments:
            command (str): command to be parsed

        Returns:
            The parsed command.

        Raises:
            ToolkitConnectionError: If the device is not connected to
                the Data Server

        """
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self.normalized_serial not in command:
                command = f"/{self.normalized_serial}" + command
        return command

    @property
    def connection(self):
        if not self._is_established:
            _logger.error(
                "Connection to the data server is not established.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return self._connection

    @property
    def device(self):
        return self._device

    @property
    def normalized_serial(self):
        if not self._is_connected:
            _logger.error(
                "The device is not connected to the data server.",
                _logger.ExceptionTypes.ToolkitConnectionError,
            )
        return self._normalized_serial

    @property
    def discovery(self):
        return self._discovery

    @property
    def is_established(self):
        return self._is_established

    @property
    def is_connected(self):
        return self._is_connected
