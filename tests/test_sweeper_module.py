import numpy as np
import pytest

from zhinst.toolkit.driver.modules.sweeper_module import SweeperModule


@pytest.fixture()
def sweeper_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_sweeper_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.sweep.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield SweeperModule(mock_connection.return_value.sweep(), session)


def test_repr(sweeper_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(sweeper_module)


def test_gridnode(sweeper_module, mock_connection, session):
    module_mock = mock_connection.return_value.sweep.return_value
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    # get
    module_mock.getString.return_value = "/dev1234/test/a/b"
    result = sweeper_module.gridnode()
    assert result.raw_tree == ("test", "a", "b")
    assert result.root.prefix_hide == "dev1234"

    module_mock.getString.return_value = "/dev1111/test/a/b"
    result = sweeper_module.gridnode()
    assert result == "/dev1111/test/a/b"

    # set
    sweeper_module.gridnode(session.devices["dev1234"].test.a.c)
    module_mock.set.assert_called_with("/gridnode", "/dev1234/test/a/c")

    sweeper_module.gridnode("dev123/test/hello")
    module_mock.set.assert_called_with("/gridnode", "dev123/test/hello")


def test_read(sweeper_module, mock_connection, session):
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    module_mock = mock_connection.return_value.sweep.return_value
    module_mock.read.return_value = {
        "/awgcontrol": np.array([0]),
        "/device": ["1234"],
        "/dev1234/demods/0/sample": [
            [
                {
                    "header": {"systemtime": np.array([1643040922025522])},
                    "x": np.array([[1, 2, 3, 4, 5]]),
                    "y": np.array([[1, 2, 4, 4, 5]]),
                    "testsignal": np.array([[9, 9, 9, 9, 9]]),
                }
            ],
        ],
    }
    result = sweeper_module.read()
    assert len(result) == 3
    result = result[session.devices["dev1234"].demods[0].sample]
    assert "systemtime" in result[0][0]["header"]
    assert np.allclose(result[0][0]["x"], np.array([[1, 2, 3, 4, 5]]))
    assert np.allclose(result[0][0]["y"], np.array([[1, 2, 4, 4, 5]]))
    assert np.allclose(result[0][0]["testsignal"], np.array([[9, 9, 9, 9, 9]]))


def test_finish(sweeper_module):
    sweeper_module.finish()
    sweeper_module.raw_module.finish.assert_called_once()


def test_progress(sweeper_module):
    sweeper_module.progress()
    sweeper_module.raw_module.progress.assert_called_once()
