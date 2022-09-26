import json
from array import array
from collections import OrderedDict
from unittest import mock
from unittest.mock import patch

import pytest

from zhinst.toolkit.driver.nodes.command_table_node import CommandTableNode
from zhinst.toolkit.driver.devices.shfsg import SHFSG


@pytest.fixture()
def command_table_node(shfsg_no_ct_schema):
    yield CommandTableNode(
        shfsg_no_ct_schema.root,
        ("sgchannels", "0", "awg", "commandtable"),
        device_type="shfsg",
    )


@pytest.fixture()
def shfsg_no_ct_schema(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_dev1234_shfsg.json"
    with json_path.open("r", encoding="UTF-8") as file:

        nodes_json = file.read()
        f = json.loads(nodes_json)
        f.pop("/dev1234/sgchannels/0/awg/commandtable/schema")
        nodes_json = json.dumps(f)
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.getString.return_value = ""
    yield SHFSG("DEV1234", "SHFSG8", session)


def test_attributes_init_node(command_table_node):
    assert command_table_node._device_type == "shfsg"
    assert command_table_node.raw_tree == ("sgchannels", "0", "awg", "commandtable")


def test_ct_schema_load_from_device(shfsg, mock_connection):
    ct_schema = '{\n  "$schema": "https://json-schema.org/draft-04/schema#",\n  "title": "AWG Command Table Schema",\n}\n'
    d = {
        "/dev1234/sgchannels/0/awg/commandtable/schema": [
            {"timestamp": 31066847852080, "flags": 0, "vector": ct_schema}
        ]
    }
    schema_rturn = OrderedDict(d)
    mock_connection.return_value.get.return_value = schema_rturn
    assert shfsg.sgchannels[0].awg.commandtable.schema() == ct_schema


def test_correct_ct_node_schema_loaded(shfsg_no_ct_schema):
    mock_json = {"test ": 123}
    with patch(
        "builtins.open", mock.mock_open(read_data=json.dumps(mock_json))
    ) as mock_open:
        assert (
            shfsg_no_ct_schema.sgchannels[0].awg.commandtable.load_validation_schema()
            == mock_json
        )


@pytest.mark.parametrize(
    "payload, validate",
    [
        (
            {
                "header": {"version": "1.1", "userString": "Test string"},
                "table": [],
            },
            True,
        ),
        (
            {
                "header": {"version": "1.1", "userString": "Test string"},
                "table": [],
            },
            False,
        ),
        (
            json.dumps(
                {
                    "header": {"version": "1.1", "userString": "Test string"},
                    "table": [],
                }
            ),
            False,
        ),
    ],
)
def test_ct_node_upload_to_device(
    payload, validate, mock_connection, command_table_node
):
    mock_connection.return_value.set = mock.Mock(side_effect=RuntimeError)
    command_table_node.check_status = mock.Mock(return_value=True)
    command_table_node.upload_to_device(payload, validate=validate)
    mock_connection.return_value.setVector.assert_called_with(
        "/dev1234/sgchannels/0/awg/commandtable/data",
        ('{"header": {"version": "1.1", "userString": "Test string"}, "table": []}'),
    )


def test_ct_upload_failed(mock_connection, command_table_node):
    mock_connection.return_value.set = mock.Mock(side_effect=RuntimeError)
    command_table_node.check_status = mock.Mock(return_value=False)
    ct = (
        {
            "header": {"version": "1.1", "userString": "Test string"},
            "table": [],
        },
    )
    with pytest.raises(RuntimeError):
        command_table_node.upload_to_device(ct, validate=False)


@pytest.fixture
def shfsg_ct_node(mock_connection, shfsg_no_ct_schema):
    schema = {
        "$schema": "https://json-schema.org/draft-04/schema#",
        "header": {"version": "1.1", "userString": "Test string"},
        "table": [],
    }
    mock_connection.return_value.get.return_value = OrderedDict(
        [
            (
                "/dev1234/sgchannels/0/awg/commandtable/data",
                {
                    "timestamp": array("q", [3880906635]),
                    "value": [schema],
                },
            )
        ]
    )
    return CommandTableNode(
        shfsg_no_ct_schema.root,
        ("sgchannels", "0", "awg", "commandtable"),
        device_type="shfsg",
    )


def test_ct_node_load_from_device_correct_data(shfsg_ct_node, mock_connection):
    ct = shfsg_ct_node.load_from_device()
    assert ct.as_dict() == {
        "header": {"version": "1.1", "userString": "Test string"},
        "table": [],
    }


def test_ct_node_load_from_device_correct_node(shfsg_ct_node, mock_connection):
    shfsg_ct_node.load_from_device()
    mock_connection.return_value.get.assert_called_with(
        "/dev1234/sgchannels/0/awg/commandtable/data", settingsonly=False, flat=True
    )


def test_ct_node_ct_not_supported(command_table_node):
    command_table_node._device_type = "shfasdddsssss132"
    with pytest.raises(KeyError) as e_info:
        command_table_node.load_validation_schema()


def test_ct_node_check_status_3bit_up(command_table_node, mock_connection):
    mock_connection.return_value.getInt.return_value = 8
    with pytest.raises(RuntimeError):
        command_table_node.check_status()


def test_ct_node_check_status_1bit_up(command_table_node, mock_connection):
    mock_connection.return_value.getInt.return_value = 1
    assert command_table_node.check_status() is True

    mock_connection.return_value.getInt.return_value = 2
    assert command_table_node.check_status() is False


def test_ct_node_status_called(command_table_node, mock_connection):
    mock_connection.return_value.getInt.return_value = 1
    command_table_node.check_status()
    mock_connection.return_value.getInt.assert_called_with(
        "/dev1234/sgchannels/0/awg/commandtable/status"
    )
