import pytest

from zhinst.toolkit.driver.devices.uhfli import AWG, UHFLI
from zhinst.toolkit.nodetree import Node


@pytest.fixture()
def uhfli(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_uhfli.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json
    mock_connection.return_value.getString.return_value = ""

    yield UHFLI("DEV1234", "UHFLI", session)


def test_repr(uhfli):
    assert repr(uhfli) == "UHFLI(UHFLI,DEV1234)"


def test_awg(data_dir, mock_connection, uhfli):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    assert len(uhfli.awgs) == 1
    assert isinstance(uhfli.awgs[0], AWG)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(uhfli.awgs["*"], AWG)
    assert isinstance(uhfli.awgs["*"], Node)

    # test command table
    assert not uhfli.awgs[0].commandtable


def test_awg_option_not_found(data_dir, mock_connection, uhfli):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    mock_connection.return_value.getString.return_value = "FOOBAR"
    assert len(uhfli.awgs) == 1
    assert isinstance(uhfli.awgs[0], Node)
