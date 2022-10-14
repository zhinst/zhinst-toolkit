from pathlib import Path
from unittest.mock import patch, PropertyMock

import pytest

from zhinst.toolkit import Session
from zhinst.toolkit.driver.devices.shfqa import SHFQA
from zhinst.toolkit.driver.devices.shfqc import SHFQC
from zhinst.toolkit.driver.devices.shfsg import SHFSG


@pytest.fixture()
def data_dir(request):
    yield Path(request.fspath).parent / "data"


@pytest.fixture()
def mock_connection():
    with patch("zhinst.toolkit.session.core.ziDAQServer", autospec=True) as connection:
        type(connection.return_value).port = PropertyMock(return_value=8004)
        type(connection.return_value).host = PropertyMock(return_value="localhost")
        type(connection.return_value).api_level = PropertyMock(return_value=6)
        yield connection


@pytest.fixture()
def nodedoc_zi_json(data_dir):
    json_path = data_dir / "nodedoc_zi.json"
    with json_path.open("r", encoding="UTF-8") as file:
        return file.read()


@pytest.fixture()
def session(nodedoc_zi_json, mock_connection):
    mock_connection.return_value.listNodesJSON.return_value = nodedoc_zi_json
    yield Session("localhost")


@pytest.fixture()
def hf2_session(mock_connection):
    mock_connection.return_value.getString.return_value = "HF2DataServer"
    type(mock_connection.return_value).port = PropertyMock(return_value=8005)
    yield Session("localhost", hf2=True)


@pytest.fixture()
def shfqa(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_shfqa.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.getString.return_value = ""
    with patch(
        "zhinst.toolkit.driver.devices.shfqa.utils.max_qubits_per_channel",
        autospec=True,
    ) as max_qubits:
        max_qubits.return_value = 16
        yield SHFQA("DEV1234", "SHFQA4", session)


@pytest.fixture()
def shfsg(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_shfsg.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.getString.return_value = ""
    yield SHFSG("DEV1234", "SHFSG8", session)


@pytest.fixture()
def shfqc(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_shfqc.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.getString.return_value = ""
    yield SHFQC("DEV1234", "SHFQC", session)


@pytest.fixture()
def zi_devices_json(data_dir):
    json_path = data_dir / "zi_devices.json"
    with json_path.open("r", encoding="UTF-8") as file:
        return file.read()


@pytest.fixture()
def nodedoc_dev1234_json(data_dir):
    json_path = data_dir / "nodedoc_dev1234.json"
    with json_path.open("r", encoding="UTF-8") as file:
        return file.read()


@pytest.fixture()
def mock_sweeper_daq():
    with patch(
        "zhinst.toolkit.driver.modules.shfqa_sweeper.ziDAQServer", autospec=True
    ) as connection:
        yield connection
