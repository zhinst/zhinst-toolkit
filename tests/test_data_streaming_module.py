import numpy as np
import pytest

from zhinst.toolkit.driver.modules.data_streaming_module import DataStreamingModule


@pytest.fixture
def data_streaming_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.dataStreamingModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    return DataStreamingModule(
        mock_connection.return_value.dataStreamingModule(),
        session,
    )


def test_repr(data_streaming_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(data_streaming_module)


def test_read(data_streaming_module, mock_connection, session):
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    module_mock.read.return_value = {
        "/dev1234/demods/0/sample.x": np.array([1, 2, 3, 4, 5]),
        "/dev1234/timestamp": np.array([11, 22, 33, 44, 55]),
    }
    result = data_streaming_module.read()
    assert len(result) == 2
    result0 = result[session.devices["dev1234"].demods[0].sample.x]
    assert (result0 == np.array([1, 2, 3, 4, 5])).all()
    result1 = result[session.devices["dev1234"].timestamp]
    assert (result1 == np.array([11, 22, 33, 44, 55])).all()


def test_subscribe(data_streaming_module, mock_connection):
    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    data_streaming_module.subscribe(data_streaming_module.test.sample.x)
    module_mock.subscribe.assert_called_with("/test/sample.x")


def test_unsubscribe(data_streaming_module, mock_connection):
    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    data_streaming_module.unsubscribe(data_streaming_module.test.sample.x)
    module_mock.unsubscribe.assert_called_with("/test/sample.x")


def test_execute(data_streaming_module, mock_connection):
    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    data_streaming_module.execute()
    module_mock.execute.assert_called_with()


def test_finish(data_streaming_module, mock_connection):
    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    data_streaming_module.finish()
    module_mock.finish.assert_called_with()


def test_finished(data_streaming_module, mock_connection):
    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    data_streaming_module.finished()
    module_mock.finished.assert_called_with()


def test_progress(data_streaming_module, mock_connection):
    module_mock = mock_connection.return_value.dataStreamingModule.return_value
    data_streaming_module.progress()
    module_mock.progress.assert_called_with()
