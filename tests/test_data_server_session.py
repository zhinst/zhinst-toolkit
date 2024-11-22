import json
from unittest.mock import MagicMock, patch

import pytest

from zhinst.toolkit import Session
import zhinst.toolkit.driver.modules as tk_modules
from zhinst.toolkit.nodetree import Node


def test_setup(mock_connection, session):
    mock_connection.assert_called_once_with(
        "localhost", 8004, 6, allow_version_mismatch=False
    )
    mock_connection.return_value.listNodesJSON.assert_called_once_with("/zi/*")
    assert repr(session) == "DataServerSession(localhost:8004)"
    assert not session.is_hf2_server
    assert session.server_host == "localhost"
    assert session.server_port == 8004


def test_setup_hf2(mock_connection, hf2_session):
    mock_connection.assert_called_once_with(
        "localhost", 8005, 1, allow_version_mismatch=False
    )
    mock_connection.return_value.listNodesJSON.assert_not_called()
    assert repr(hf2_session) == "HF2DataServerSession(localhost:8005)"
    assert hf2_session.is_hf2_server


def test_allow_mismatch_not_supported(mock_connection, nodedoc_zi_json):
    mock_daq = MagicMock()
    mock_daq.listNodesJSON.return_value = nodedoc_zi_json

    def create_daq(*args, **kwargs):
        if "allow_version_mismatch" in kwargs:
            raise TypeError("allow_version_mismatch not recognized")
        return mock_daq

    mock_connection.side_effect = create_daq
    Session("localhost", 8004)
    mock_connection.assert_any_call("localhost", 8004, 6, allow_version_mismatch=False)
    mock_connection.assert_called_with("localhost", 8004, 6)


# Passing "allow_version_mismatch" does not cause an error, even if the underlying
# zhinst.core does not recognize this flag.
def test_allow_mismatch_passed_but_not_supported(mock_connection, nodedoc_zi_json):
    mock_daq = MagicMock()
    mock_daq.listNodesJSON.return_value = nodedoc_zi_json

    def create_daq(*args, **kwargs):
        if "allow_version_mismatch" in kwargs:
            raise TypeError("allow_version_mismatch not recognized")
        return mock_daq

    mock_connection.side_effect = create_daq
    Session("localhost", 8004, allow_version_mismatch=True)
    mock_connection.assert_any_call("localhost", 8004, 6, allow_version_mismatch=True)
    mock_connection.assert_called_with("localhost", 8004, 6)


def test_allow_mismatch_default(mock_connection, nodedoc_zi_json):
    mock_daq = MagicMock()
    mock_daq.listNodesJSON.return_value = nodedoc_zi_json

    def create_daq(*args, **kwargs):
        return mock_daq

    mock_connection.side_effect = create_daq
    Session("localhost", 8004)
    mock_connection.assert_called_once_with(
        "localhost", 8004, 6, allow_version_mismatch=False
    )


def test_existing_connection(nodedoc_zi_json, mock_connection):
    mock_connection.listNodesJSON.return_value = nodedoc_zi_json
    mock_connection.getString.return_value = "DataServer"

    Session.from_existing_connection(mock_connection)
    mock_connection.assert_not_called()
    mock_connection.getString.assert_called_with("/zi/about/dataserver")
    mock_connection.listNodesJSON.assert_called_once_with("/zi/*")

    Session.from_existing_connection(mock_connection)
    with pytest.raises(RuntimeError) as e_info:
        Session("localhost", connection=mock_connection, hf2=True)


def test_existing_connection_hf2(mock_connection):
    mock_connection.getString.return_value = "HF2DataServer"

    Session("localhost", connection=mock_connection)
    mock_connection.assert_not_called()
    mock_connection.getString.assert_called_with("/zi/about/dataserver")
    mock_connection.listNodesJSON.assert_not_called()

    Session("localhost", connection=mock_connection, hf2=True)
    with pytest.raises(RuntimeError) as e_info:
        Session("localhost", connection=mock_connection, hf2=False)


def test_wrong_port(mock_connection):
    def setup_side_effect(host, port, level):
        if level > 1:
            raise RuntimeError("Unsupported API level")
        return mock_connection.return_value

    mock_connection.side_effect = setup_side_effect
    # Test HF2 server
    mock_connection.return_value.getString.return_value = "HF2DataServer"
    Session("localhost", 8005)
    mock_connection.assert_called_with("localhost", 8005, 1)

    Session("localhost", 8005, hf2=True)
    with pytest.raises(RuntimeError) as e_info:
        Session("localhost", 8005, hf2=False)


def test_unkown_init_error(mock_connection):
    mock_connection.side_effect = RuntimeError("Unkown")
    with pytest.raises(RuntimeError) as e_info:
        Session("localhost", 8005, hf2=False)


def test_connect_device(
    zi_devices_json, mock_connection, session, nodedoc_dev1234_json
):
    connected_devices = ""

    def get_string_side_effect(arg):
        if arg == "/zi/devices":
            return zi_devices_json
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    def connect_device_side_effect(serial, _):
        nonlocal connected_devices
        devices = [key for key in json.loads(zi_devices_json).keys()]
        if serial.upper() not in devices:
            raise RuntimeError("device not visible to server")
        if serial not in connected_devices:
            if not connected_devices:
                connected_devices = serial
            else:
                connected_devices = connected_devices + "," + serial

    mock_connection.return_value.connectDevice.side_effect = connect_device_side_effect
    mock_connection.return_value.listNodesJSON.return_value = nodedoc_dev1234_json

    # device not visible
    with pytest.raises(KeyError) as e_info:
        session.connect_device("dev1111")
    assert "dev1111" in e_info.value.args[0].lower()

    # device visible
    device = session.connect_device("dev1234")
    mock_connection.return_value.connectDevice.assert_called_with("dev1234", "1GbE")
    assert device.serial == "dev1234"
    assert device.device_type == "Test"
    assert device.__class__.__name__ == "BaseInstrument"

    # access connected device
    assert "dev1234" in session.devices
    assert device == session.devices["dev1234"]
    assert len(session.devices) == 1
    for dev in session.devices:
        assert dev == "dev1234"

    # delete existing device
    # connot be overwritten
    with pytest.raises(LookupError) as e_info:
        session.devices["dev1234"] = None

    session.disconnect_device("dev1234")
    # Can be called as often as wanted
    session.disconnect_device("dev1234")


def test_connect_device_autodetection(
    zi_devices_json, mock_connection, session, nodedoc_dev1234_json
):
    connected_devices = ""
    selected_interface = ""

    def get_string_side_effect(arg):
        if arg == "/zi/devices":
            return zi_devices_json
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    def connect_device_side_effect(serial, interface):
        nonlocal connected_devices, selected_interface
        devices = [key for key in json.loads(zi_devices_json).keys()]
        if serial.upper() not in devices:
            raise RuntimeError("device not visible to server")
        if serial not in connected_devices:
            if not connected_devices:
                connected_devices = serial
            else:
                connected_devices = connected_devices + "," + serial
        selected_interface = interface

    mock_connection.return_value.connectDevice.side_effect = connect_device_side_effect
    mock_connection.return_value.listNodesJSON.return_value = nodedoc_dev1234_json

    session.connect_device("dev1234")
    assert selected_interface == "1GbE"
    connected_devices = ""
    selected_interface = ""

    for none_interface in ("none", "", "unknown"):
        zi_devices = json.loads(zi_devices_json)
        zi_devices["DEV1234"]["INTERFACE"] = none_interface
        zi_devices_json = json.dumps(zi_devices)

        session.connect_device("dev1234")
        assert selected_interface == "1GbE"
    connected_devices = ""
    selected_interface = ""

    for gbe_interface in ("1GBE", "1GbE"):
        zi_devices = json.loads(zi_devices_json)
        zi_devices["DEV1234"]["INTERFACES"] = f"{gbe_interface},USB"
        zi_devices_json = json.dumps(zi_devices)

        session.connect_device("dev1234")
        assert selected_interface == "1GbE"
    connected_devices = ""
    selected_interface = ""

    zi_devices = json.loads(zi_devices_json)
    zi_devices["DEV1234"]["INTERFACES"] = "USB"
    zi_devices_json = json.dumps(zi_devices)

    session.connect_device("dev1234")
    assert selected_interface == "USB"
    connected_devices = ""
    selected_interface = ""

    zi_devices = json.loads(zi_devices_json)
    zi_devices["DEV1234"]["INTERFACES"] = "PCIE"
    zi_devices_json = json.dumps(zi_devices)

    session.connect_device("dev1234")
    assert selected_interface == "PCIE"


def test_connect_device_h2(mock_connection, hf2_session, nodedoc_dev1234_json):
    def connect_device_side_effect(serial, _):
        if serial == "dev1111":
            raise RuntimeError("dev1111 not visible")

    mock_connection.return_value.connectDevice.side_effect = connect_device_side_effect

    def get_string_side_effect(arg):
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    mock_connection.return_value.listNodesJSON.return_value = nodedoc_dev1234_json

    # device not visible
    with pytest.raises(RuntimeError) as e_info:
        hf2_session.connect_device("dev1111")
    assert "dev1111" in e_info.value.args[0].lower()

    # device visible
    device = hf2_session.connect_device("dev1234")
    mock_connection.return_value.connectDevice.assert_called_with("dev1234", "USB")
    assert device.serial == "dev1234"
    assert device.device_type == "Test"
    assert device.__class__.__name__ == "BaseInstrument"

    # access connected device
    assert "dev1234" in hf2_session.devices
    assert device == hf2_session.devices["dev1234"]
    assert len(hf2_session.devices) == 1
    for dev in hf2_session.devices:
        assert dev == "dev1234"

    with pytest.raises(RuntimeError) as e_info:
        hf2_session.devices.add_hf2_device("dev1234")

    # connect non HF2 device
    with patch("zhinst.toolkit.session.core.ziDiscovery", autospec=True) as discovery:
        discovery.return_value.get.return_value = {"devicetype": "Test234"}
        with pytest.raises(RuntimeError) as e_info:
            hf2_session.connect_device("dev5678")
    assert "dev5678" in e_info.value.args[0].lower()
    assert "test234" in e_info.value.args[0].lower()

    # unknown connection error
    mock_connection.return_value.getString.side_effect = RuntimeError("Unkown")
    with pytest.raises(RuntimeError) as e_info:
        hf2_session.connect_device("dev5555")
    assert "Unkown" == e_info.value.args[0]


def test_devices_visible(mock_connection, session, hf2_session):
    session.devices.visible()
    mock_connection.return_value.getString.assert_called_with("/zi/devices/visible")

    def get_string_side_effect(arg):
        if arg == "/zi/devices/visible":
            raise RuntimeError()

    mock_connection.return_value.getString.side_effect = get_string_side_effect
    with patch("zhinst.toolkit.session.core.ziDiscovery", autospec=True) as discovery:
        hf2_session.devices.visible()
        discovery.return_value.findAll.assert_called_once()


def test_sync(mock_connection, session):
    session.sync()
    mock_connection.return_value.sync.assert_called_once()


def test_poll(mock_connection, session):
    # default call
    # empty result
    result = session.poll()
    mock_connection.return_value.poll.assert_called_with(0.1, 500, flags=0, flat=True)
    assert not result

    # with result
    # TODO


def test_modules_repr(session):
    assert repr(session.modules) == "LabOneModules(localhost:8004)"


def test_raw_path_to_node(data_dir, mock_connection, session, zi_devices_json):
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices":
            return zi_devices_json
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect
    result = session.raw_path_to_node("/dev1234/test/a/b/c")
    assert result.raw_tree == ("test", "a", "b", "c")
    assert result.root.prefix_hide == "dev1234"

    # Only absolut paths are supported
    with pytest.raises(ValueError) as e_info:
        session.raw_path_to_node("dev1234/test/a/b/c")

    # Not connected device
    with pytest.raises(RuntimeError) as e_info:
        session.raw_path_to_node("/dev1235/test/a/b/c")

    # with optional module
    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.dataAcquisitionModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    result = session.raw_path_to_node("/device", module=session.modules.daq)
    assert result.raw_tree == ("device",)
    assert result.root.connection == session.modules.daq.raw_module

    # zi node
    session.raw_path_to_node("/zi/about/commit")


def test_awg_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    awg_module = session.modules.awg
    assert awg_module == session.modules.awg
    mock_connection.return_value.awgModule.assert_called_once()
    assert isinstance(awg_module, tk_modules.BaseModule)
    assert isinstance(awg_module.device, Node)


def test_daq_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.dataAcquisitionModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    daq_module = session.modules.daq
    assert daq_module == session.modules.daq
    mock_connection.return_value.dataAcquisitionModule.assert_called_once()
    assert isinstance(daq_module, tk_modules.DAQModule)
    assert isinstance(daq_module.device, Node)


def test_device_settings_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_device_settings_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.deviceSettings.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    device_settings_module = session.modules.device_settings
    assert device_settings_module == session.modules.device_settings
    mock_connection.return_value.deviceSettings.assert_called_once()
    assert isinstance(device_settings_module, tk_modules.DeviceSettingsModule)
    assert isinstance(device_settings_module.device, Node)


def test_impedance_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_impedance_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.impedanceModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    impedance_module = session.modules.impedance
    assert impedance_module == session.modules.impedance
    mock_connection.return_value.impedanceModule.assert_called_once()
    assert isinstance(impedance_module, tk_modules.ImpedanceModule)
    assert isinstance(impedance_module.device, Node)


def test_mds_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.multiDeviceSyncModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    mds_module = session.modules.mds
    assert mds_module == session.modules.mds
    mock_connection.return_value.multiDeviceSyncModule.assert_called_once()
    assert isinstance(mds_module, tk_modules.BaseModule)
    assert isinstance(mds_module.device, Node)


def test_pid_advisor_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_pid_advisor_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.pidAdvisor.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    pid_advisor_module = session.modules.pid_advisor
    assert pid_advisor_module == session.modules.pid_advisor
    mock_connection.return_value.pidAdvisor.assert_called_once()
    assert isinstance(pid_advisor_module, tk_modules.PIDAdvisorModule)
    assert isinstance(pid_advisor_module.device, Node)


def test_precompensation_advisor_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_precomensation_advisor_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.precompensationAdvisor.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    precompensation_advisor_module = session.modules.precompensation_advisor
    assert precompensation_advisor_module == session.modules.precompensation_advisor
    mock_connection.return_value.precompensationAdvisor.assert_called_once()
    assert isinstance(
        precompensation_advisor_module, tk_modules.PrecompensationAdvisorModule
    )
    assert isinstance(precompensation_advisor_module.device, Node)


def test_qa_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.quantumAnalyzerModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    qa_module = session.modules.qa
    assert qa_module == session.modules.qa
    mock_connection.return_value.quantumAnalyzerModule.assert_called_once()
    assert isinstance(qa_module, tk_modules.BaseModule)
    assert isinstance(qa_module.device, Node)


def test_scope_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_scope_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.scopeModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    scope_module = session.modules.scope
    assert scope_module == session.modules.scope
    mock_connection.return_value.scopeModule.assert_called_once()
    assert isinstance(scope_module, tk_modules.BaseModule)
    assert isinstance(scope_module.device, Node)


def test_sweeper_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_sweeper_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.sweep.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    sweeper_module = session.modules.sweeper
    assert sweeper_module == session.modules.sweeper
    mock_connection.return_value.sweep.assert_called_once()
    assert isinstance(sweeper_module, tk_modules.SweeperModule)
    assert isinstance(sweeper_module.device, Node)


def test_shfqa_sweeper(session):
    sweeper = session.modules.shfqa_sweeper
    assert sweeper == session.modules.shfqa_sweeper
    assert isinstance(sweeper, tk_modules.SHFQASweeper)


def test_session_wide_transaction(
    mock_connection, nodedoc_dev1234_json, session, shfqa, shfsg
):
    # Hack devices into the created once
    session._devices._devices = {"dev1": shfqa, "dev2": shfsg}

    with session.set_transaction():
        session.mds.groups[0].keepalive(1)
        shfqa.qachannels[0].centerfreq(100)
        shfsg.sgchannels[1].awg.time(100)
        session.mds.groups[0].keepalive(4)

    mock_connection.return_value.set.assert_called_once_with(
        [
            ("/zi/mds/groups/0/keepalive", 1),
            ("/dev1234/qachannels/0/centerfreq", 1000000000.0),  # lower bound ;)
            ("/dev1234/sgchannels/1/awg/time", 100),
            ("/zi/mds/groups/0/keepalive", 4),
        ]
    )

    # impossible to create two transactions
    with pytest.raises(RuntimeError) as e_info:
        with session.set_transaction():
            with session.set_transaction():
                session.mds.groups[0].keepalive(1)

    # add new device during transaction
    mock_connection.return_value.getString.side_effect = ["dev1234", "MFLI", ""]
    mock_connection.return_value.listNodesJSON.return_value = nodedoc_dev1234_json
    with session.set_transaction():
        session.mds.groups[0].keepalive(1)
        shfqa.qachannels[0].centerfreq(100)
        session.devices["dev1234"].demods[0].enable(1)
    mock_connection.return_value.set.assert_called_with(
        [
            ("/zi/mds/groups/0/keepalive", 1),
            ("/dev1234/qachannels/0/centerfreq", 1000000000.0),  # lower bound ;)
            ("/dev1234/demods/0/enable", 1),
        ]
    )
