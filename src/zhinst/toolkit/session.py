"""Module for managing a session to a Data Server through zhinst.core."""

import json
import typing as t
from collections.abc import MutableMapping
from enum import IntFlag
from pathlib import Path
from contextlib import contextmanager

import zhinst.toolkit.driver.devices as tk_devices
import zhinst.toolkit.driver.modules as tk_modules
from zhinst.toolkit.exceptions import ToolkitError
from zhinst import core
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import lazy_property, NodeDict
from zhinst.toolkit.nodetree.nodetree import Transaction


class Devices(MutableMapping):
    """Mapping class for the connected devices.

    Maps the connected devices from data server to lazy device objects.
    On every access the connected devices are read from the data server. This
    ensures that even if devices get connected/disconnected through another
    session the list will be up to date.

    Args:
        session: An active session to the data server.
    """

    def __init__(self, session: "Session"):
        self._session = session
        self._devices: t.Dict[str, tk_devices.DeviceType] = {}
        self._device_classes = tk_devices.DEVICE_CLASS_BY_MODEL

    def __getitem__(self, key) -> tk_devices.DeviceType:
        key = key.lower()
        if key in self.connected():
            if key not in self._devices:
                self._devices[key] = self._create_device(key)
                # start a transaction if the session has a ongoing one
                if self._session.multi_transaction.in_progress():
                    self._devices[key].root.transaction.start(
                        self._session.multi_transaction.add
                    )
            return self._devices[key]
        self._devices.pop(key, None)
        raise KeyError(key)

    def __setitem__(self, *_):
        raise LookupError(
            "Illegal operation. Can not add a device manually. Devices must be "
            "connected through the session (session.connect_device)."
        )

    def __delitem__(self, key):
        self._devices.pop(key, None)

    def __iter__(self):
        return iter(self.connected())

    def __len__(self):
        return len(self.connected())

    def _create_device(self, serial: str) -> tk_devices.DeviceType:
        """Creates a new device object.

        Maps the device type to the correct instrument class (The default is
        the ``BaseInstrument`` which is a generic instrument class that supports
        all devices).

        Warning:
            The device must be connected to the data server.

        Args:
            serial: Device serial

        Returns:
            Newly created instrument object

        Raises:
            RuntimeError: If the device is not connected to the data server
        """
        dev_type = self._session.daq_server.getString(f"/{serial}/features/devtype")
        return self._device_classes.get(dev_type, tk_devices.BaseInstrument)(
            serial, dev_type, self._session
        )

    def connected(self) -> t.List[str]:
        """Get a list of devices connected to the data server.

        Returns:
            List of all connected devices.
        """
        return (
            self._session.daq_server.getString("/zi/devices/connected")
            .lower()
            .split(",")
        )

    def visible(self) -> t.List[str]:
        """Get a list of devices visible to the data server.

        Returns:
            List of all connected devices.
        """
        return (
            self._session.daq_server.getString("/zi/devices/visible").lower().split(",")
        )

    def created_devices(self) -> t.ValuesView[tk_devices.DeviceType]:
        """View on all created device.

        The list contains all toolkit device objects that have been created for
        the underlying session.

        Warning: This is not equal to the devices connected to the data server!
            Use the iterator of the `Devices` class directly to get all devices
            connected to the data server.
        """
        return self._devices.values()


class HF2Devices(Devices):
    """Mapping class for the connected HF2 devices.

    Maps the connected devices from data server to lazy device objects.
    It derives from the general ``Devices`` class and adds the special handling
    for the HF2 data server. Since the HF2 Data Server is based on the API Level
    1 it as a much more restricted API. This means it is not possible to get
    the connected or visible devices from the data server. This class must
    track the connected devices itself and use discovery to mimic the
    behavior of the new data server used for the other devices.
    """

    def _create_device(self, serial: str) -> tk_devices.BaseInstrument:
        """Creates a new device object.

        Maps the device type to the correct instrument class (The default is
        the ``BaseInstrument`` which is a generic instrument class that supports
        all devices).

        Warning:
            The device must already be connected to the data server

        Args:
            serial: Device serial

        Returns:
            Newly created instrument object

        Raises:
            RuntimeError: If the device is not connected to the data server
            ToolkitError: DataServer is HF2, but the device is not.
        """
        try:
            return super()._create_device(serial)
        except RuntimeError as error:
            if "ZIAPINotFoundException" in error.args[0]:
                discovery = core.ziDiscovery()
                discovery.find(serial)
                dev_type = discovery.get(serial)["devicetype"]
                raise ToolkitError(
                    "Can only connect HF2 devices to an HF2 data "
                    f"server. {serial} identifies itself as a {dev_type}."
                ) from error
            raise

    def connected(self) -> t.List[str]:
        """Get a list of devices connected to the data server.

        Returns:
            List of all connected devices.
        """
        return list(self._devices.keys())

    def visible(self) -> t.List[str]:
        """Get a list of devices visible to the data server.

        Returns:
            List of all connected devices.
        """
        return core.ziDiscovery().findAll()

    def add_hf2_device(self, serial: str) -> None:
        """Add a new HF2 device.

        Since the HF2 data server is not able to report its connected devices
        toolkit manually needs to update the list of known connected devices.

        Args:
            serial: Serial of the HF2 device

        Raises:
            ToolkitError: If the device was already added in that session.
        """
        if serial in self._devices:
            raise ToolkitError(f"Can only create one instance of {serial}.")
        self._devices[serial] = self._create_device(serial)


class ModuleHandler:
    """Modules of LabOne.

    Handler for all additional so called modules by LabOne. A LabOne module is
    bound to a user session but creates a independent session to the Data Server.
    This has the advantage that they do not interfere with the user session. It
    also means that creating a session causes additional resources allocation,
    both at the client and the data server. New modules should therefore only be
    instantiated with care.

    Toolkit holds a lazy generated instance of all modules. This ensures that
    not more than one modules of each type gets created by accident and that the
    access to the modules is optimized.

    Of course there are many use cases where more than one module of a single
    type is required. This class therefore also exposes a ``create`` function for
    each LabOne module. These functions create a unmanaged instance of that
    module (unmanaged means toolkit does not hold an instance of that module).

    Args:
        session: Active user session
        server_host: Host address of the session
        server_port: Port of the session
    """

    def __init__(self, session: "Session"):
        self._session = session

    def __repr__(self):
        return str(
            "LabOneModules("
            f"{self._session.daq_server.host}:{self._session.daq_server.port})"
        )

    def create_awg_module(self) -> tk_modules.BaseModule:
        """Create an instance of the AwgModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `awg`.

        Returns:
            Created module
        """
        return tk_modules.BaseModule(
            self._session.daq_server.awgModule(), self._session
        )

    def create_daq_module(self) -> tk_modules.DAQModule:
        """Create an instance of the DataAcquisitionModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `daq`.

        Returns:
            Created module
        """
        return tk_modules.DAQModule(
            self._session.daq_server.dataAcquisitionModule(), self._session
        )

    def create_device_settings_module(self) -> tk_modules.DeviceSettingsModule:
        """Create an instance of the DeviceSettingsModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `device_settings_module`.

        Returns:
            Created module
        """
        return tk_modules.DeviceSettingsModule(
            self._session.daq_server.deviceSettings(), self._session
        )

    def create_impedance_module(self) -> tk_modules.ImpedanceModule:
        """Create an instance of the ImpedanceModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `impedance_module`.

        Returns:
            Created module
        """
        return tk_modules.ImpedanceModule(
            self._session.daq_server.impedanceModule(), self._session
        )

    def create_mds_module(self) -> tk_modules.BaseModule:
        """Create an instance of the MultiDeviceSyncModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `mds_module`.

        Returns:
            Created module
        """
        return tk_modules.BaseModule(
            self._session.daq_server.multiDeviceSyncModule(), self._session
        )

    def create_pid_advisor_module(self) -> tk_modules.PIDAdvisorModule:
        """Create an instance of the PidAdvisorModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `pid_advisor_module`.

        Returns:
            Created module
        """
        return tk_modules.PIDAdvisorModule(
            self._session.daq_server.pidAdvisor(), self._session
        )

    def create_precompensation_advisor_module(
        self,
    ) -> tk_modules.PrecompensationAdvisorModule:
        """Create an instance of the PrecompensationAdvisorModule.

        In contrast to core.ziDAQServer.precompensationAdvisor() a nodetree property
        is added.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `precompensation_advisor_module`.

        Returns:
            Created module
        """
        return tk_modules.PrecompensationAdvisorModule(
            self._session.daq_server.precompensationAdvisor(), self._session
        )

    def create_qa_module(self) -> tk_modules.BaseModule:
        """Create an instance of the QuantumAnalyzerModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `qa_module`.

        Returns:
            Created module
        """
        return tk_modules.BaseModule(
            self._session.daq_server.quantumAnalyzerModule(), self._session
        )

    def create_scope_module(self) -> tk_modules.ScopeModule:
        """Create an instance of the ScopeModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `awg_module`.

        Returns:
            Created module
        """
        return tk_modules.ScopeModule(
            self._session.daq_server.scopeModule(), self._session
        )

    def create_sweeper_module(self) -> tk_modules.SweeperModule:
        """Create an instance of the SweeperModule.

        The resulting Module will have the nodetree accessible. The underlying
        zhinst.core Module can be accessed through the `raw_module`
        property.

        The new instance establishes a new session to the DataServer.
        New instances should therefor be created carefully since they consume
        resources.

        The new module is not managed by toolkit. A managed instance is provided
        by the property `sweeper_module`.

        Returns:
            Created module
        """
        return tk_modules.SweeperModule(self._session.daq_server.sweep(), self._session)

    def create_shfqa_sweeper(self) -> tk_modules.SHFQASweeper:
        """Create an instance of the SHFQASweeper.

        For now the general sweeper module does not support the SHFQA. However a
        python based implementation called ``SHFSweeper`` does already provide
        this functionality. The ``SHFSweeper`` is part of the ``zhinst`` module
        and can be found in the utils.

        Toolkit wraps around the ``SHFSweeper`` and exposes a interface that is
        similar to the LabOne modules, meaning the parameters are exposed in a
        node tree like structure.

        In addition a new session is created. This has the benefit that the
        sweeper implementation does not interfere with the the commands and
        setups from the user.

        Returns:
            Created object
        """
        return tk_modules.SHFQASweeper(self._session)

    @lazy_property
    def awg(self) -> tk_modules.BaseModule:
        """Managed instance of the awg module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_awg_module`` to create an unmanaged instance)
        """
        return self.create_awg_module()

    @lazy_property
    def daq(self) -> tk_modules.DAQModule:
        """Managed instance of the daq module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_daq_module`` to create an unmanaged instance)
        """
        return self.create_daq_module()

    @lazy_property
    def device_settings(self) -> tk_modules.DeviceSettingsModule:
        """Managed instance of the device settings module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_device_settings_module`` to create an
        unmanaged instance)
        """
        return self.create_device_settings_module()

    @lazy_property
    def impedance(self) -> tk_modules.ImpedanceModule:
        """Managed instance of the impedance module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_awg_module`` to create an unmanaged instance)
        """
        return self.create_impedance_module()

    @lazy_property
    def mds(self) -> tk_modules.BaseModule:
        """Managed instance of the multi device sync module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_mds_module`` to create an unmanaged instance)
        """
        return self.create_mds_module()

    @lazy_property
    def pid_advisor(self) -> tk_modules.PIDAdvisorModule:
        """Managed instance of the pid advisor module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_pid_advisor_module`` to create an unmanaged
        instance)
        """
        return self.create_pid_advisor_module()

    @lazy_property
    def precompensation_advisor(self) -> tk_modules.PrecompensationAdvisorModule:
        """Managed instance of the precompensation advisor module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_precompensation_advisor_module`` to create an
        unmanaged instance)
        """
        return self.create_precompensation_advisor_module()

    @lazy_property
    def qa(self) -> tk_modules.BaseModule:
        """Managed instance of the quantum analyzer module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_qa_module`` to create an unmanaged instance)
        """
        return self.create_qa_module()

    @lazy_property
    def scope(self) -> tk_modules.ScopeModule:
        """Managed instance of the scope module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_scope_module`` to create an unmanaged
        instance)
        """
        return self.create_scope_module()

    @lazy_property
    def sweeper(self) -> tk_modules.SweeperModule:
        """Managed instance of the sweeper module.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_sweeper_module`` to create an unmanaged instance)
        """
        return self.create_sweeper_module()

    @lazy_property
    def shfqa_sweeper(self) -> tk_modules.SHFQASweeper:
        """Managed instance of the shfqa sweeper implementation.

        Managed means that only one instance is created
        and is held inside the connection Manager. This makes it easier to access
        the modules from within toolkit, since creating a module requires
        resources. (``use create_shfqa_sweeper`` to create an unmanaged
        instance)
        """
        return self.create_shfqa_sweeper()


class PollFlags(IntFlag):
    """Flags for polling Command.

    DETECT_AND_THROW(12):
        Detect data loss holes and throw EOFError exception

    DETECT(8):
        Detect data loss holes

    FILL(1):
        Fill holes

    DEFAULT(0):
        No Flags

    Can be combined with bitwise operations

    >>> PollFlags.FILL | PollFlags.DETECT
        <PollFlags.DETECT|FILL: 9>
    """

    DETECT_AND_THROW = 12
    DETECT = 8
    FILL = 1
    DEFAULT = 0


class Session(Node):
    """Session to a data server.

    Zurich Instruments devices use a server-based connectivity methodology.
    Server-based means that all communication between the user and the
    instrument takes place via a computer program called a server, the data
    sever. The data sever recognizes available instruments and manages all
    communication between the instrument and the host computer on one side, and
    communication to all the connected clients on the other side. (For more
    information on the architecture please refer to the user manual
    http://docs.zhinst.com/labone_programming_manual/introduction.html)

    The entry point into for any connection is therefore a client session to a
    existing data sever. This class represents a single client session to a
    data server. The session enables the user to connect to one or multiple
    instruments (also creates the dedicated objects for each device), access
    the LabOne modules and poll data. In short it is the only object the user
    need to create by himself.

    Info:
        Except for the HF2 a single session can be used to connect to all
        devices from Zurich Instruments. Since the HF2 is historically based on
        another data server called the hf2 data server it is not possible to
        connect HF2 devices a "normal" data server and also not possible to
        connect devices apart from HF2 to the hf2 data server.

    Args:
        server_host: Host address of the data server (e.g. localhost)
        server_port: Port number of the data server. If not specified the session
            uses the default port 8004 (8005 for HF2 if specified).
            (default = None)
        hf2: Flag if the session should be established with an HF2 data sever or
            the "normal" one for all other devices. If not specified the session
            will detect the type of the data server based on the port.
            (default = None)
        connection: Existing DAQ server object. If specified the session will
            not create a new session to the data server but reuse the passed
            one. (default = None)
        allow_version_mismatch: if set to True, the connection to the data-server
            will succeed even if the data-server is on a different version of LabOne.
            If False, an exception will be raised if the data-server is on a
            different version. (default = False)

    .. versionchanged:: 0.8.0
        Added `allow_version_mismatch` argument.
    """

    def __init__(
        self,
        server_host: str,
        server_port: t.Optional[int] = None,
        *,
        hf2: t.Optional[bool] = None,
        connection: t.Optional[core.ziDAQServer] = None,
        allow_version_mismatch: bool = False,
    ):
        self._is_hf2_server = bool(hf2)
        if connection is not None:
            self._is_hf2_server = "HF2" in connection.getString("/zi/about/dataserver")
            if hf2 and not self._is_hf2_server:
                raise ToolkitError(
                    "hf2 flag was set but the passed "
                    "DAQServer instance is not a HF2 data server."
                )
            if hf2 is False and self._is_hf2_server:
                raise ToolkitError(
                    "hf2 flag was set but the passed "
                    "DAQServer instance is a HF2 data server."
                )
            self._daq_server = connection
        else:
            server_port = server_port if server_port else 8004
            if self._is_hf2_server and server_port == 8004:
                server_port = 8005
            try:
                self._daq_server = self._create_daq(
                    server_host, server_port, allow_version_mismatch
                )
            except RuntimeError as error:
                if "Unsupported API level" not in error.args[0]:
                    raise
                if hf2 is None:
                    self._is_hf2_server = True
                    self._daq_server = core.ziDAQServer(
                        server_host,
                        server_port,
                        1,
                    )
                elif not hf2:
                    raise ToolkitError(
                        "hf2 Flag was reset but the specified "
                        f"server at {server_host}:{server_port} is a "
                        "HF2 data server."
                    ) from error

        self._devices = HF2Devices(self) if self._is_hf2_server else Devices(self)
        self._modules = ModuleHandler(self)

        hf2_node_doc = Path(__file__).parent / "resources/nodedoc_hf2_data_server.json"
        nodetree = NodeTree(
            self._daq_server,
            prefix_hide="zi",
            list_nodes=["/zi/*"],
            preloaded_json=json.loads(hf2_node_doc.open("r").read())
            if self._is_hf2_server
            else None,
        )
        super().__init__(nodetree, tuple())
        self._multi_transaction = Transaction(self.root)

    def __repr__(self):
        return str(
            f"{'HF2' if self._is_hf2_server else ''}DataServerSession("
            f"{self._daq_server.host}:{self._daq_server.port})"
        )

    @classmethod
    def from_existing_connection(cls, connection: core.ziDAQServer) -> "Session":
        """Initialize Session from an existing connection.

        Args:
            connection: Existing connection.

        .. versionadded:: 0.4.0
        """
        is_hf2_server = "HF2" in connection.getString("/zi/about/dataserver")
        return cls(
            server_host=connection.host,
            server_port=connection.port,
            hf2=is_hf2_server,
            connection=connection,
        )

    def connect_device(
        self, serial: str, *, interface: t.Optional[str] = None
    ) -> tk_devices.DeviceType:
        """Establish a connection to a device.

        Info:
            It is allowed to call this function for an already connected device.
            In that case the function simply returns the device object of the
            device.

        If the interface is not specified the interface will be auto detected.
        Meaning one of the available interfaces will be selected, prioritizing
        1GbE over USB.

        Args:
            serial: Serial number of the device, e.g. *'dev12000'*.
                The serial number can be found on the back panel of the
                instrument.
            interface: Device interface (e.g. = "1GbE"). If not specified
                the default interface from the discover is used.

        Returns:
            Device object

        Raises:
            KeyError: Device is not found.
            RuntimeError: Connection failed.
        """
        serial = serial.lower()
        if serial not in self._devices:
            if not interface:
                if self._is_hf2_server:
                    interface = "USB"
                else:
                    # Take interface from the discovery
                    dev_info = json.loads(self.daq_server.getString("/zi/devices"))[
                        serial.upper()
                    ]
                    interface = t.cast(str, dev_info["INTERFACE"])
                    undefined_interfaces = ("none", "", "unknown")
                    if interface.lower() in undefined_interfaces:
                        interface = (
                            "1GbE"
                            if "1gbe" in dev_info["INTERFACES"].lower()
                            else dev_info["INTERFACES"].split(",")[0]
                        )
            self._daq_server.connectDevice(serial, interface)
            if isinstance(self._devices, HF2Devices):
                self._devices.add_hf2_device(serial)
        return self._devices[serial]

    def disconnect_device(self, serial: str) -> None:
        """Disconnect a device.

        Warning:
            This function will return immediately. The disconnection of the
            device may not yet finished.

        Args:
            serial: Serial number of the device, e.g. *'dev12000'*.
                The serial number can be found on the back panel of the instrument.
        """
        self._devices.pop(serial, None)
        self.daq_server.disconnectDevice(serial)

    def sync(self) -> None:
        """Synchronize all connected devices.

        Synchronization in this case means creating a defined state.

        The following steps are performed:
            * Ensures that all set commands have been flushed to the device
            * Ensures that get and poll commands only return data which was
              recorded after the sync command. (ALL poll buffers are cleared!)
            * Blocks until all devices have cleared their busy flag.

        Warning:
            The sync is performed for all devices connected to the DAQ server

        Warning:
            This command is a blocking command that can take a substantial
            amount of time.

        Raises:
            RuntimeError: ZIAPIServerException: Timeout during sync of device
        """
        self.daq_server.sync()

    def poll(
        self,
        recording_time: float = 0.1,
        *,
        timeout: float = 0.5,
        flags: PollFlags = PollFlags.DEFAULT,
    ) -> t.Dict[Node, t.Dict[str, t.Any]]:
        """Polls all subscribed data from the data server.

        Poll the value changes in all subscribed nodes since either subscribing
        or the last poll (assuming no buffer overflow has occurred on the Data
        Server).

        Args:
            recording_time: Defines the duration of the poll in seconds. (Note that not
                only the newly recorded values are polled but all values since
                either subscribing or the last poll). Needs to be larger than
                zero. (default = 0.1)
            timeout: Adds an additional timeout in seconds on top of
                `recording_time`. Only relevant when communicating in a slow
                network. In this case it may be set to a value larger than the
                expected round-trip time in the network. (default = 0.5)
            flags: Flags for the polling (see :class `PollFlags`:)

        Returns:
            Polled data in a dictionary. The key is a `Node` object and the
            value is a dictionary with the raw data from the device
        """
        return NodeDict(
            self.daq_server.poll(
                recording_time, int(timeout * 1000), flags=flags.value, flat=True
            )
        )

    def raw_path_to_node(
        self, raw_path: str, *, module: tk_modules.ModuleType = None
    ) -> Node:
        """Converts a raw node path string into a Node object.

        The device that this strings belongs to must be connected to the Data
        Server. Optionally a module can be specified to which the node belongs to.
        (The module is only an additional search path, meaning even if a module
        is specified the node can belong to a connected device.)

        Args:
            raw_path: Raw node path (e.g. /dev1234/relative/path/to/node).

        Returns:
            Corresponding toolkit node object.

        Raises:
            ValueError: If the `raw_path` does not start with a leading dash.
            ToolkitError: If the node does not belong to the optional module or
                to a connected device.

        .. versionchanged:: 0.5.3

            Changed `RuntimeError` to `ValueError`.
        """
        if not raw_path.startswith("/"):
            raise ValueError(
                f"{raw_path} does not seem to be an absolute path. "
                "It must start with a leading slash."
            )
        if module is not None:
            node = module.root.raw_path_to_node(raw_path)
            if node.raw_tree[0] in module.root:
                return node
        try:
            serial = raw_path.split("/")[1]
            if serial == "zi":
                return self.root.raw_path_to_node(raw_path)
            return self.devices[serial].root.raw_path_to_node(raw_path)
        except KeyError as error:
            raise ToolkitError(
                f"Node belongs to a device({raw_path.split('/')[1]}) not connected to "
                "the Data Server."
            ) from error

    @contextmanager
    def set_transaction(self) -> t.Generator[None, None, None]:
        """Context manager for a transactional set.

        Can be used as a context in a with statement and bundles all node set
        commands into a single transaction. This reduces the network overhead
        and often increases the speed.

        In comparison to the device level transaction manager this manager
        affects all devices that are connected to the Session and bundles all
        set commands into a single transaction.

        Within the with block a set commands to a node will be buffered
        and bundled into a single command at the end automatically.
        (All other operations, e.g. getting the value of a node, will not be
        affected)

        Warning:
            The set is always performed as deep set if called on device nodes.

        Examples:
            >>> with session.set_transaction():
                    device1.test[0].a(1)
                    device2.test[0].a(2)

        .. versionadded:: 0.4.0
        """
        self._multi_transaction.start()
        for device in self.devices.created_devices():
            device.root.transaction.start(self._multi_transaction.add)
        self.root.transaction.start(self._multi_transaction.add)
        try:
            yield
            self._daq_server.set(self._multi_transaction.result())
        finally:
            for device in self.devices.created_devices():
                device.root.transaction.stop()
            self.root.transaction.stop()
            self._multi_transaction.stop()

    @property
    def multi_transaction(self) -> Transaction:
        """Flag if a session wide transaction is in progress.

        .. versionadded:: 0.4.0
        """
        return self._multi_transaction

    @property
    def devices(self) -> Devices:
        """Mapping for the connected devices."""
        return self._devices

    @property
    def modules(self) -> ModuleHandler:
        """Modules of LabOne."""
        return self._modules

    @property
    def is_hf2_server(self) -> bool:
        """Flag if the data server is a HF2 Data Server."""
        return self._is_hf2_server

    @property
    def daq_server(self) -> core.ziDAQServer:
        """Managed instance of the core.ziDAQServer."""
        return self._daq_server

    @property
    def server_host(self) -> str:
        """Server host."""
        return self._daq_server.host

    @property
    def server_port(self) -> int:
        """Server port."""
        return self._daq_server.port

    def clone_underlying_session(self) -> core.ziDAQServer:
        """Create a new session to the data server.

        Create a new core.ziDAQServer connected to the same data-server this
        session is connected to.
        """
        # Don't execute version checking. When clone_underlying_session is called,
        # a connection has already been made, so checking again would be redundant.
        return self._create_daq(self.server_host, self.server_port, True)

    def _create_daq(
        self,
        server_host: str,
        server_port: int,
        allow_version_mismatch: bool,
    ):
        """Create a new session to the data server.

        Attempt to pass the allow_version_mismatch flag. Fallback in case
        zhinst.core does not support it yet.
        """
        api_level = 1 if self._is_hf2_server else 6
        try:
            return core.ziDAQServer(
                server_host,
                server_port,
                api_level,
                allow_version_mismatch=allow_version_mismatch,
            )
        except TypeError as error:
            if "allow_version_mismatch" not in error.args[0]:
                raise
            return core.ziDAQServer(server_host, server_port, api_level)
