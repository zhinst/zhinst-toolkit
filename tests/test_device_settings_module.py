import pytest
from pathlib import Path

from zhinst.toolkit.driver.modules.device_settings_module import DeviceSettingsModule


@pytest.fixture()
def device_settings_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_device_settings_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.deviceSettings.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield DeviceSettingsModule(mock_connection.return_value.deviceSettings(), session)


def test_repr(device_settings_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(
        device_settings_module
    )


def test_load_from_file(device_settings_module):
    device_settings_module.raw_module.getInt.return_value = 1
    device_settings_module.raw_module.get.return_value = {
        "/finished": {"timestamp": [0], "value": [1]}
    }

    device_settings_module.load_from_file(Path("/path/to/file.json"), "dev1234")
    device_settings_module.raw_module.set.assert_any_call("/device", "dev1234")
    device_settings_module.raw_module.set.assert_any_call("/filename", "file")
    device_settings_module.raw_module.set.assert_any_call("/path", "/path/to")
    device_settings_module.raw_module.set.assert_any_call("/command", "load")
    device_settings_module.raw_module.execute.assert_called_once()


def test_load_from_file_timeout(device_settings_module):
    device_settings_module.raw_module.getInt.return_value = 0
    device_settings_module.raw_module.get.return_value = {
        "/finished": {"timestamp": [0], "value": [0]}
    }

    with pytest.raises(TimeoutError):
        device_settings_module.load_from_file(
            Path("/path/to/file.json"), "dev1234", timeout=0.01
        )


def test_save_to_file(device_settings_module):
    device_settings_module.raw_module.getInt.return_value = 1
    device_settings_module.raw_module.get.return_value = {
        "/finished": {"timestamp": [0], "value": [1]}
    }

    device_settings_module.save_to_file(Path("/path/to/file.json"), "dev1234")
    device_settings_module.raw_module.set.assert_any_call("/device", "dev1234")
    device_settings_module.raw_module.set.assert_any_call("/filename", "file")
    device_settings_module.raw_module.set.assert_any_call("/path", "/path/to")
    device_settings_module.raw_module.set.assert_any_call("/command", "save")
    device_settings_module.raw_module.execute.assert_called_once()


def test_save_to_file_timeout(device_settings_module):
    device_settings_module.raw_module.getInt.return_value = 0
    device_settings_module.raw_module.get.return_value = {
        "/finished": {"timestamp": [0], "value": [0]}
    }

    with pytest.raises(TimeoutError):
        device_settings_module.save_to_file(
            Path("/path/to/file.json"), "dev1234", timeout=0.01
        )


def test_read(device_settings_module):
    device_settings_module.raw_module.read.return_value = {"/device": "test"}
    result = device_settings_module.read()
    assert device_settings_module.device in result
    assert result[device_settings_module.device] == "test"
