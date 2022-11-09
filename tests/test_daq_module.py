import numpy as np
import pytest

from zhinst.toolkit.driver.modules.daq_module import DAQModule


@pytest.fixture()
def daq_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.dataAcquisitionModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield DAQModule(mock_connection.return_value.dataAcquisitionModule(), session)


def test_repr(daq_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(daq_module)


def test_triggernode(daq_module, mock_connection, session):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    # get
    module_mock.getString.return_value = "/dev1234/sample.a.b"
    result = daq_module.triggernode()
    assert result.raw_tree == ("sample", "a", "b")
    assert result.root.prefix_hide == "dev1234"

    module_mock.getString.return_value = "/dev1234/test/a/b"
    result = daq_module.triggernode()
    assert result.raw_tree == ("test", "a", "b")
    assert result.root.prefix_hide == "dev1234"

    module_mock.getString.return_value = "/dev1111/test/a/b"
    result = daq_module.triggernode()
    assert result == "/dev1111/test/a/b"

    # set
    daq_module.triggernode(session.devices["dev1234"].test.a.c)
    module_mock.set.assert_called_with("/triggernode", "/dev1234/test/a/c")

    daq_module.triggernode(session.devices["dev1234"].sample.a.c)
    module_mock.set.assert_called_with("/triggernode", "/dev1234/sample.a.c")

    daq_module.triggernode("dev123/test/hello")
    module_mock.set.assert_called_with("/triggernode", "dev123/test/hello")


def test_read(daq_module, mock_connection, session):
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    module_mock.read.return_value = {
        "/awgcontrol": np.array([0]),
        "/device": ["1234"],
        "/dev1234/demods/0/sample.x.avg": [
            {
                "header": {"systemtime": np.array([1643040922025522])},
                "timestamp": np.array([[1, 2, 3, 4, 5]]),
                "value": np.array([[1, 2, 3, 4, 5]]),
            }
        ],
    }
    result = daq_module.read()
    assert len(result) == 3
    result = result[session.devices["dev1234"].demods[0].sample.x.avg]
    assert "systemtime" in result[0].header
    assert (result[0].time == np.array([[0, 1, 2, 3, 4]]) / 60e6).all()
    assert (result[0].value == np.array([[1, 2, 3, 4, 5]])).all()
    assert result[0].frequency is None
    assert result[0].shape == (1, 5)

    result = daq_module.read(raw=True)
    assert len(result) == 3
    result = result[session.devices["dev1234"].demods[0].sample.x.avg]
    assert "systemtime" in result[0]["header"]
    assert (result[0]["timestamp"] == np.array([[1, 2, 3, 4, 5]])).all()
    assert (result[0]["value"] == np.array([[1, 2, 3, 4, 5]])).all()

    module_mock.read.return_value = {
        "/awgcontrol": np.array([0]),
        "/device": ["1234"],
        "/dev1234/demods/0/sample.x.avg": [
            {
                "header": {"systemtime": np.array([1643040922025522])},
                "timestamp": np.array([[1, 2, 3, 4, 5]]),
                "value": np.array([[1, 2, 3, 4, 5]]),
            },
            {
                "header": {"systemtime": np.array([1643040922040000])},
                "timestamp": np.array([[6, 7, 8, 9, 10]]),
                "value": np.array([[5, 4, 3, 2, 1]]),
            },
        ],
        "/dev1234/demods/1/sample.xiy.fft": [
            {
                "header": {"gridcoldelta": np.array([0.00059733])},
                "timestamp": np.array([[1, 2, 3, 4, 5]]),
                "value": np.array([[9, 9, 9, 9, 9]]),
            },
        ],
    }
    result = daq_module.read()
    assert len(result) == 4
    result0 = result[session.devices["dev1234"].demods[0].sample.x.avg]
    result1 = result[session.devices["dev1234"].demods[1].sample.xiy.fft]
    assert "systemtime" in result0[0].header
    assert (result0[0].time == np.array([[0, 1, 2, 3, 4]]) / 60e6).all()
    assert (result0[0].value == np.array([[1, 2, 3, 4, 5]])).all()
    assert result0[0].frequency is None
    assert result0[0].shape == (1, 5)
    assert (result0[1].time == np.array([[0, 1, 2, 3, 4]]) / 60e6).all()
    assert (result0[1].value == np.array([[5, 4, 3, 2, 1]])).all()
    assert result0[1].frequency is None
    assert result0[1].shape == (1, 5)
    assert "gridcoldelta" in result1[0].header
    assert np.allclose(
        result1[0].frequency,
        np.array([[-1.19466e-03, -5.9733e-04, -5.42101e-20, 5.9733e-04, 1.19466e-03]]),
    )
    assert (result1[0].value == np.array([[9, 9, 9, 9, 9]])).all()
    assert result1[0].time is None
    assert result1[0].shape == (1, 5)


def test_subscribe(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.subscribe(daq_module.test.sample.x.avg)
    module_mock.subscribe.assert_called_with("/test/sample.x.avg")


def test_unsubscribe(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.unsubscribe(daq_module.test.sample.x.avg)
    module_mock.unsubscribe.assert_called_with("/test/sample.x.avg")


def test_execute(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.execute()
    module_mock.execute.assert_called_with()


def test_finish(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.finish()
    module_mock.finish.assert_called_with()


def test_finished(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.finished()
    module_mock.finished.assert_called_with()


def test_progress(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.progress()
    module_mock.progress.assert_called_with()


def test_trigger(daq_module, mock_connection):
    module_mock = mock_connection.return_value.dataAcquisitionModule.return_value
    daq_module.trigger()
    module_mock.trigger.assert_called_with()
