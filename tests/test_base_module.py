import numpy as np
import pytest

from pathlib import Path

from zhinst.toolkit.driver.modules.base_module import BaseModule


@pytest.fixture()
def base_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield BaseModule(mock_connection.return_value.awgModule(), session)


def test_repr(base_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(base_module)


def test_raw_module(base_module, mock_connection):
    assert base_module.raw_module == mock_connection.return_value.awgModule()


def test_device(zi_devices_json, base_module, mock_connection):
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

    # get
    mock_connection.return_value.awgModule.return_value.getString.return_value = ""
    result = base_module.device()
    assert result == ""

    mock_connection.return_value.awgModule.return_value.getString.return_value = (
        "dev1234"
    )
    result = base_module.device()
    assert result.serial == "dev1234"

    # set
    base_module.device("dev1634")
    mock_connection.return_value.awgModule.return_value.set.assert_called_with(
        "/device", "dev1634"
    )

    base_module.device(result)
    mock_connection.return_value.awgModule.return_value.set.assert_called_with(
        "/device", "dev1234"
    )


def test_wait_done(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    module_mock.finished.return_value = 1
    module_mock.progress.return_value = np.array([1])
    base_module.wait_done()

    module_mock.finished.return_value = 0
    module_mock.progress.return_value = np.array([0.1])
    with pytest.raises(TimeoutError) as e_info:
        base_module.wait_done(timeout=0.01)


def test_subscribe(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    base_module.subscribe(base_module.test)
    module_mock.subscribe.assert_called_with("/test")


def test_subscribe_str(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    base_module.subscribe(base_module.test.node_info.path)
    module_mock.subscribe.assert_called_with("/test")


def test_unsubscribe(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    base_module.unsubscribe(base_module.test)
    module_mock.unsubscribe.assert_called_with("/test")


def test_unsubscribe_str(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    base_module.unsubscribe(base_module.test.node_info.path)
    module_mock.unsubscribe.assert_called_with("/test")


def test_execute(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    base_module.execute()
    module_mock.execute.assert_called_once()


def test_set_path(base_module, mock_connection):
    module_mock = mock_connection.return_value.awgModule.return_value
    base_module.directory(Path("test"))
    module_mock.set.assert_called_with("/directory", str(Path("test").resolve()))
    base_module.directory("test")
    module_mock.set.assert_called_with("/directory", "test")
