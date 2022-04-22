from pathlib import Path
from unittest.mock import patch

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
    with patch(
        "zhinst.toolkit.session.ziPython.ziDAQServer", autospec=True
    ) as connection:
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
def hf2_session(data_dir, mock_connection):
    mock_connection.return_value.getString.return_value = "HF2DataServer"
    yield Session("localhost", hf2=True)


@pytest.fixture()
def shfqa(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_shfqa.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.getString.return_value = ""
    with patch(
        "zhinst.toolkit.driver.devices.shfqa.deviceutils.max_qubits_per_channel",
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
