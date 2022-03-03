import pytest

from zhinst.toolkit.driver.devices.hdawg import AWG, HDAWG
from zhinst.toolkit.nodetree import Node


@pytest.fixture()
def hdawg(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_hdawg.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.listNodes.return_value = [
        "/dev1234/awgs/0",
        "/dev1234/awgs/1",
        "/dev1234/awgs/2",
        "/dev1234/awgs/3",
    ]
    mock_connection.return_value.getString.return_value = ""

    yield HDAWG("DEV1234", "HDAWG4", session)


def test_repr(hdawg):
    assert repr(hdawg) == "HDAWG(HDAWG4,DEV1234)"


def test_enable_qccs_mode(mock_connection, hdawg):
    hdawg.enable_qccs_mode()
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/system/clocks/referenceclock/source", "zsync"),
            ("/dev1234/dios/0/interface", 0),
            ("/dev1234/dios/0/mode", "qccs"),
            ("/dev1234/dios/0/drive", 12),
            ("/dev1234/awgs/0/dio/strobe/slope", "off"),
            ("/dev1234/awgs/1/dio/strobe/slope", "off"),
            ("/dev1234/awgs/2/dio/strobe/slope", "off"),
            ("/dev1234/awgs/3/dio/strobe/slope", "off"),
            ("/dev1234/awgs/0/dio/valid/polarity", "none"),
            ("/dev1234/awgs/1/dio/valid/polarity", "none"),
            ("/dev1234/awgs/2/dio/valid/polarity", "none"),
            ("/dev1234/awgs/3/dio/valid/polarity", "none"),
        ]
    )
    mock_connection.reset_mock()
    with hdawg.set_transaction():
        hdawg.enable_qccs_mode()
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/system/clocks/referenceclock/source", "zsync"),
            ("/dev1234/dios/0/interface", 0),
            ("/dev1234/dios/0/mode", "qccs"),
            ("/dev1234/dios/0/drive", 12),
            ("/dev1234/awgs/0/dio/strobe/slope", "off"),
            ("/dev1234/awgs/1/dio/strobe/slope", "off"),
            ("/dev1234/awgs/2/dio/strobe/slope", "off"),
            ("/dev1234/awgs/3/dio/strobe/slope", "off"),
            ("/dev1234/awgs/0/dio/valid/polarity", "none"),
            ("/dev1234/awgs/1/dio/valid/polarity", "none"),
            ("/dev1234/awgs/2/dio/valid/polarity", "none"),
            ("/dev1234/awgs/3/dio/valid/polarity", "none"),
        ]
    )


def test_awg(data_dir, mock_connection, hdawg):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    assert len(hdawg.awgs) == 4
    assert isinstance(hdawg.awgs[0], AWG)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(hdawg.awgs["*"], AWG)
    assert isinstance(hdawg.awgs["*"], Node)
