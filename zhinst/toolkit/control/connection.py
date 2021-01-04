# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import json
import zhinst.ziPython as zi
from zhinst.toolkit.interface import DeviceTypes
import zhinst.ziPython as zi

class ToolkitConnectionError(Exception):
    """Exception specific to the zhinst.toolkit ZIConnection class."""

    pass


class ZIConnection:
    """Connection to a Zurich Instruments data server object. 
    
    Wraps around the basic functionality of connecting to the dataserver, 
    connecting a device to the server, and setting and getting node values. It 
    also holds an awg module object that implements the `daq.awgModule` module 
    as well as DAQ module and Sweeper Module connections.
    
    Arguments:
        connection_details: Part of the instrument config.
    
    Attributes:
        connection_details (ZIAPI)
        daq (zi.ziDAQServer): data server object from zhinst.ziPython
    
    Properties:
        established (bool): A flag showing if a connection has been established.
        awg_module (AWGModuleConnection)
        daq_module (DAQModuleConnection)
        sweeper_module (SweeperModuleConnection)

    """

    def __init__(self, connection_details):
        self._connection_details = connection_details
        self._daq = None
        self._awg = None

    def connect(self):
        """Established a connection to the data server. 
        
        Uses the connection details (host, port, api level) specified in the 
        'connection_details' to open a `zi.ziDAQServer` data server object that
        is used for all communication to the data server.

        Raises:
            ToolkitConnectionError: if connection to the Data Server could not 
                be established

        """
        try:
            self._daq = zi.ziDAQServer(
                self._connection_details.host,
                self._connection_details.port,
                self._connection_details.api,
            )
        except RuntimeError:
            raise ToolkitConnectionError(
                f"No connection could be established with the connection details:"
                f"{self._connection_details}"
            )
        if self._daq is not None:
            print(
                f"Successfully connected to data server at "
                f"{self._connection_details.host}:"
                f"{self._connection_details.port} "
                f"api version: {self._connection_details.api}"
            )
            self._awg_module = AWGModuleConnection(self._daq)
            self._daq_module = DAQModuleConnection(self._daq)
            self._sweeper_module = SweeperModuleConnection(self._daq)
        else:
            raise ToolkitConnectionError(
                f"No connection could be established with the connection details:"
                f"{self._connection_details}"
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
            ToolkitConnectionError if the could not be established. 

        """        
        if self._daq is None:
            raise ToolkitConnectionError("No existing connection to data server")
        if any(k is None for k in [serial, interface]):
            raise ToolkitConnectionError(
                "To connect a Zurich Instruments' device, youd need a serial and an interface [1gbe or usb]"
            )
        self._daq.connectDevice(serial, interface)
        print(
            f"Successfully connected to device {serial.upper()} on interface {interface.upper()}"
        )
        self._awg_module.update(device=serial, index=0)

    def set(self, *args):
        """Wrapper around the `zi.ziDAQServer.set()` method of the API.
        
        Passes all arguments to the undelying method.
        
        Raises:
            ToolkitConnectionError: is the connection is not yet established
        
        Returns:
            the value returned from `daq.set(...)`
        
        """
        if not self.established:
            raise ToolkitConnectionError("The connection is not yet established.")
        return self._daq.set(*args)

    def get(self, *args, **kwargs):
        """Wrapper around the `zi.ziDAQServer.get(...)` method of the API.
        
        Passes all arguments and keyword arguments to the underlying method.
        
        Raises:
            ToolkitConnectionError: is the connection is not yet established
        
        Returns:
            the value returned from `daq.get(...)`
        
        """
        if not self.established:
            raise ToolkitConnectionError("The connection is not yet established.")
        return self._daq.get(*args, **kwargs)

    def get_sample(self, *args, **kwargs):
        """Wrapper around the `daq.getSample(...)` method of the API. 
        
        Passes all arguments and keyword arguments to the underlying method. 
        Used only for certain streaming nodes on the UHFLI or MFLI devices.

        Raises:
            ToolkitConnectionError: is the connection is not yet established
        
        Returns:
            the value returned from `daq.getSample(...)`
        
        """
        if not self.established:
            raise ToolkitConnectionError("The connection is not yet established.")
        return self._daq.getSample(*args, **kwargs)

    def list_nodes(self, *args, **kwargs):
        """Wrapper around the `daq.listNodesJSON(...)` method of the API. 
        
        Passes all arguments and keyword arguemnts to the undelying method.

        Raises:
            ToolkitConnectionError: is the connection is not yet established
        
        Returns:
            the value returned from `daq.listNodesJSON(...)`
        
        """
        if not self.established:
            raise ToolkitConnectionError("The connection is not yet established.")
        return self._daq.listNodesJSON(*args, **kwargs)

    @property
    def awg_module(self):
        return self._awg_module

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
    
    Inherits from `DAQModuleConnection` but uses the `daq.seep()` module instead.
    
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
    
    """

    def __init__(self, device, discovery):
        self._connection = None
        self._device = device
        self.normalized_serial = None
        self.discovery = discovery

    def setup(self, connection: ZIConnection = None):
        """Establishes the connection to the data server.
        
        Keyword Arguments:
            connection (ZIConnection): An existing connection can be passed as 
                an argument. (default: None)

        """
        if connection is None:
            details = self._device._config._api_config
            self._connection = ZIConnection(details)
        else:
            self._connection = connection
        if not self._connection.established:
            self._connection.connect()
    
    def _normalize_serial(self, serial):
        try:            
            device_props = self.discovery.get(self.discovery.find(serial))
            discovered_serial = device_props["deviceid"]
            return discovered_serial.lower()
        except RuntimeError:
            raise ToolkitConnectionError(f"Failed to discover a device with serial {serial}")

    def connect_device(self):
        """Connects the device to the data server."""

        if self.discovery is not None:
            self.normalized_serial = self._normalize_serial(self._device.serial)
        else:
            self.normalized_serial = self._device.serial
            
        self._connection.connect_device(
            serial=self.normalized_serial, interface=self._device.interface,
        )

    def set(self, *args):
        """Sets the value of the node for the connected device. 
        
        Parses the input arguments to either set a single node/value pair or a 
        list of node/value tuples. Eventually wraps around the daq.set(...) of 
        the API.

        Raises:
            ToolkitConnectionError if is the input arguemnts are invalid.

        Returns:
            The set value as returned from the API.

        """
        if len(args) == 2:
            settings = [(args[0], args[1])]
        elif len(args) == 1:
            settings = args[0]
        else:
            raise ToolkitConnectionError("Invalid number of arguments!")
        settings = self._commands_to_node(settings)
        return self._connection.set(settings)

    def get(self, command, valueonly=True):
        """Gets the value of the node for the connected device. 
        
        Parses the returned dictionary from the data server to output only the 
        actual value in a nice format. Wraps around the daq.get(...) of the API.

        Arguments:
            command (str): node string of the value to get
            
        Keyword Arguments:
            valueonly (bool): a flag specifying if the entire dict should be 
                returned as from the API or only the actual value 
                (default: True)

        Raises:
            ToolkitConnectionError: if no device is connected

        Returns:
            The value of the node.

        """
        if self._device is not None:
            if isinstance(command, list):
                paths = []
                for c in command:
                    paths.append(self._command_to_node(c))
                node_string = ", ".join([p for p in paths])
            elif isinstance(command, str):
                node_string = self._command_to_node(command)
            else:
                raise ToolkitConnectionError("Invalid argument!")
            if (
                self._device.device_type in [DeviceTypes.UHFLI, DeviceTypes.MFLI]
                and "sample" in command.lower()
            ):
                data = self._connection.get_sample(node_string)
                return self._get_value_from_streamingnode(data)
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
            raise ToolkitConnectionError("No device connected!")

    def get_nodetree(self, prefix: str, **kwargs):
        """Gets the entire nodetree of the connected device. 
        
        Wraps around the `daq.listNodesJSON(...)` method in zhinst.ziPython.

        Arguments:
            prefix (str): a partial node string that is passed to 
                'listNodesJSON(...)' to specify which part of the nodetree 
                to return

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
            raise ToolkitConnectionError("Something went wrong...")
        if not len(data):
            raise ToolkitConnectionError("No data returned... does the node exist?")
        new_data = dict()
        for key, data_dict in data.items():
            key = key.replace(f"/{self.normalized_serial}/", "")
            if isinstance(data_dict, list):
                data_dict = data_dict[0]
            if "value" in data_dict.keys():
                new_data[key] = data_dict["value"][0]
            if "vector" in data_dict.keys():
                new_data[key] = data_dict["vector"]
        return new_data

    def _get_value_from_streamingnode(self, data):
        """Gets the (complex) data only for specific demod sample nodes.
        
        Arguments:
            data (dict): A dictionary as returned from the Python API.
        
        Raises:
            ToolkitConnectionError: if no data is returned from the API
        
        Returns:
            The complex demod sample value.

        """
        if not isinstance(data, dict):
            raise ToolkitConnectionError("Something went wrong...")
        if not len(data):
            raise ToolkitConnectionError("No data returned... does the node exist?")
        if "x" not in data.keys() or "y" not in data.keys():
            raise ToolkitConnectionError("No 'x' or 'y' in streaming node data!")
        return data["x"][0] + 1j * data["y"][0]

    def _commands_to_node(self, settings):
        """Converts a list of command strings to a list of node paths.
        
        Parses a list of command and value pairs into a a list of node value 
        pairs that can be passed to 'ziDAQServer.set(...)'. E.g. adds the 
        device serial in front of every command.
        
        Arguments:
            settings (list): list of command/value pairs
        
        Raises:
            ToolkitConnectionError: if the command/value pairs are not 
                specified as pairs/tuples
        
        Returns:
            The parsed list.

        """
        new_settings = []
        for args in settings:
            try:
                if len(args) != 2:
                    raise ToolkitConnectionError(
                        "node/value must be specified as pairs!"
                    )
            except TypeError:
                raise ToolkitConnectionError("node/value must be specified as pairs!")
            new_settings.append((self._command_to_node(args[0]), args[1]))
        return new_settings

    def _command_to_node(self, command):
        """Converts a command string to a node path.

        Parses a single command into a node string that can be passed 
        to `ziDAQServer.set(...)`. Checks if the command starts with a '/' and 
        adds the right device serial if the command 
        does not start with '/zi/'.
        
        Arguments:
            command (str): command to be parsed
        
        Returns:
            The parsed command.
            
        """
        command = command.lower()
        if command[0] != "/":
            command = "/" + command
        if "/zi/" not in command:
            if self.normalized_serial not in command:
                command = f"/{self.normalized_serial}" + command
        return command
