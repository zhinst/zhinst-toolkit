import json
from unittest.mock import patch, Mock

import jsonref
import jsonschema
import pytest

from zhinst.toolkit.command_table import CommandTable, ParentNode, _derefence_json
from zhinst.toolkit.exceptions import ValidationError


def test_ct_clear(command_table_schema):
    ct2 = CommandTable(command_table_schema)
    ct = CommandTable(command_table_schema)
    ct.table[0].amplitude00.value = 1
    ct.header.userString = "Foo bar"
    ct.clear()
    assert ct.as_dict() == ct2.as_dict()


def test_initialize_command_table_dict_json(command_table_schema):
    obj = CommandTable(command_table_schema)
    assert isinstance(obj._ct_schema, dict)


def test_initialize_command_table_str_json(command_table_schema):
    obj = CommandTable(json.dumps(command_table_schema))
    assert isinstance(obj._ct_schema, dict)


def test_parent_node_repr():
    foo = ParentNode({}, ("table", "0", "bar", "foo"))
    assert str(foo) == "/table/0/bar/foo"


def test_command_table_header_version_22_02(command_table_schema_22_02):
    ct = CommandTable(command_table_schema_22_02)
    assert (
        ct.header.version
        == command_table_schema_22_02["definitions"]["header"]["properties"]["version"][
            "enum"
        ][0]
    )


def test_command_table_header_version_22_08(command_table_schema_22_08):
    ct = CommandTable(command_table_schema_22_08)
    assert ct.header.version == command_table_schema_22_08["version"]


def test_properties_parent_entry(command_table_schema):
    ct = CommandTable(command_table_schema)
    test_props = dir(ct.table[0])
    json_props = list(command_table_schema["definitions"]["entry"]["properties"].keys())
    assert test_props.sort() == json_props.sort()


def test_parent_entry_get_attr_underscore(command_table):
    assert command_table.table[0]._foobar is None


def test_parent_entry_get_property_attr(command_table):
    assert command_table.table[0].amplitude00.value is None


def test_list_entry_len(command_table):
    command_table.table[0]
    command_table.table[1]
    command_table.table[5]
    command_table.table[1]
    assert len(command_table.table) == 3


def test_parent_entry_contains(command_table):
    assert "value" in command_table.table[0].amplitude00
    assert "waveform" in command_table.table[0]
    assert "version" in command_table.header
    assert "canno" not in command_table.header


def test_header_parent_entry(command_table_schema):
    ct = CommandTable(command_table_schema)
    test_props = dir(ct.header)
    json_props = list(
        command_table_schema["definitions"]["header"]["properties"].keys()
    )
    assert test_props.sort() == json_props.sort()


def test_parent_entry_properties(command_table_schema):
    ct = CommandTable(command_table_schema)
    for property_ in command_table_schema["definitions"]["entry"]["properties"].keys():
        if property_ != "index":
            assert hasattr(ct.table[0], property_) is True


def test_property_get_not_existing(command_table):
    properties = (
        f'{list(command_table._ct_schema["definitions"]["entry"]["properties"].keys())}'
    )
    with pytest.raises(AttributeError, match=properties):
        command_table.table[0].this_property_cannot_exists


def test_property_set_not_existing(command_table):
    properties = (
        f'{list(command_table._ct_schema["definitions"]["entry"]["properties"].keys())}'
    )
    with pytest.raises(AttributeError, match=properties):
        command_table.table[0].this_property_cannot_exists = 123


def test_parent_entry_header(command_table_schema):
    ct = CommandTable(command_table_schema)
    r = jsonref.loads(json.dumps(command_table_schema))
    for property_ in r["definitions"]["header"]["properties"].keys():
        assert (
            ct.header.info(property_)
            == r["definitions"]["header"]["properties"][property_]
        )


def test_assert_validate_called_table_index(command_table):
    with patch("zhinst.toolkit.command_table.jsonschema.validate") as mocked_method:
        command_table.table[44]
        mocked_method.assert_called_once_with(
            instance=44,
            schema={
                "type": "integer",
                "minimum": 0,
                "maximum": 1023,
                "exclusiveMinimum": False,
                "exclusiveMaximum": False,
            },
            cls=jsonschema.validators.Draft4Validator,
        )


@pytest.mark.parametrize("value", [True, False])
def test_command_table_active_validation(command_table_schema, value):
    ct = CommandTable(command_table_schema, active_validation=value)
    assert ct.active_validation is value
    ct.active_validation = not value
    assert ct.active_validation is not value


@pytest.mark.parametrize("value", [True, False])
def test_command_table_active_validation_change_header_table_true(
    command_table_schema, value
):
    ct = CommandTable(command_table_schema)
    ct.active_validation = value
    assert ct.header._active_validation is value
    assert ct.table._active_validation is value


def test_command_table_active_validation_table(command_table_schema):
    ct = CommandTable(command_table_schema, active_validation=True)
    ct.table[0]
    with pytest.raises(ValidationError):
        ct.table[999999]
    ct = CommandTable(command_table_schema, active_validation=False)
    ct.table[999999].amplitude00.value = 1
    ct.as_dict()
    assert ct.is_valid() is False
    ct.active_validation = True
    with pytest.raises(ValidationError):
        ct.as_dict()


@pytest.mark.parametrize("state", [True, False])
def test_table_is_valid_active_validation_state_persists(command_table, state):
    command_table.active_validation = state
    command_table.is_valid() is True
    assert command_table.active_validation is state

    command_table.as_dict = Mock(side_effect=ValidationError)
    command_table.is_valid() is False
    assert command_table.active_validation is state

    with pytest.raises(ValidationError):
        command_table.is_valid(raise_for_invalid=True)
    assert command_table.active_validation is state


def test_command_table_active_validation_parent_entry(command_table_schema):
    ct = CommandTable(command_table_schema, active_validation=True)
    ct.table[0]
    with pytest.raises(ValidationError):
        ct.table[0].amplitude00.value = "abc"
    ct = CommandTable(command_table_schema, active_validation=False)
    ct.table[0].amplitude00.value = "abc"


def test_command_table_active_validation_header(command_table_schema):
    ct = CommandTable(command_table_schema, active_validation=True)
    ct.table[0]
    with pytest.raises(ValidationError):
        ct.header.userString = 213
    ct = CommandTable(command_table_schema, active_validation=False)
    ct.header.userString = 213


@pytest.mark.parametrize("input_, output", [(1, 1), (40, 40), ("foo", "foo"), (-2, -2)])
def test_assert_validate_called_parent_entry_attribute_set(
    input_, output, command_table
):
    obj = command_table.table[0]
    with patch("zhinst.toolkit.command_table.jsonschema.validate") as mocked_method:
        obj.amplitude00.value = input_
        mocked_method.assert_called_once_with(
            instance=output,
            schema={
                "description": "Amplitude scaling factor of the given AWG channel",
                "type": "number",
                "minimum": -1.0,
                "maximum": 1.0,
                "exclusiveMinimum": False,
                "exclusiveMaximum": False,
            },
            cls=jsonschema.validators.Draft4Validator,
        )


def test_parent_entry_table_index(command_table):
    with pytest.raises(AttributeError):
        command_table.table[0].index = 5321


def test_parent_entry_table_waveform(command_table):
    command_table.table[0].waveform.index = 2000
    assert command_table.table[0].waveform.index == 2000


def test_build_json_no_items(command_table):
    assert command_table.as_dict() == {
        "header": {"version": "1.1.0"},
        "table": [],
    }


def test_build_json_items(command_table_schema):
    command_table = CommandTable(command_table_schema)
    assert command_table.as_dict() == {
        "header": {"version": "1.1.0"},
        "table": [],
    }
    command_table.table[0].amplitude00.value = 1
    command_table.table[0].waveform.index = 0

    command_table.table[2].amplitude00.value = 0.5
    command_table.table[2].waveform.index = 3
    command_table.table[2].waveform.awgChannel0 = ["sigout1"]
    assert command_table.as_dict() == {
        "header": {"version": "1.1.0"},
        "table": [
            {"amplitude00": {"value": 1}, "index": 0, "waveform": {"index": 0}},
            {
                "amplitude00": {"value": 0.5},
                "index": 2,
                "waveform": {"awgChannel0": ["sigout1"], "index": 3},
            },
        ],
    }


def test_table_index_value_error(command_table_schema):
    command_table = CommandTable(command_table_schema)
    idx_min = command_table_schema["definitions"]["tableindex"]["minimum"]

    with pytest.raises(ValidationError):
        command_table.table[idx_min - 5]
    command_table.table[idx_min + 1]


def test_load_completed_command_table(command_table_schema, command_table_completed):
    ct = CommandTable(command_table_schema)
    ct.update(command_table_completed)
    assert command_table_completed == ct.as_dict()

    ct.update(json.dumps(command_table_completed))
    assert command_table_completed == ct.as_dict()


def test_modify_completed_command_table(command_table_schema, command_table_completed):
    ct = CommandTable(command_table_schema)
    ct.update(command_table_completed)
    assert ct.table[0].amplitude00.as_dict() == {
        "increment": False,
        "value": 0,
    }
    ct.table[0].amplitude00.value = 1
    ct.table[0].amplitude00.increment = True
    assert ct.table[0].amplitude00.as_dict() == {
        "increment": True,
        "value": 1,
    }


def test_command_table_schema_version_mismatch(
    command_table_schema, command_table_completed
):
    command_table_completed["header"]["version"] = "2.0"
    ct = CommandTable(command_table_schema)
    with pytest.raises(ValidationError):
        ct.update(command_table_completed)


def test_parent_delete_attribute(command_table):
    command_table.table[0].amplitude00.value = 1
    command_table.table[0].waveform.index = 10
    assert command_table.table[0].as_dict() == {
        "amplitude00": {"value": 1},
        "waveform": {"index": 10},
    }
    command_table.table[0].amplitude00 = None
    assert command_table.table[0].as_dict() == {"waveform": {"index": 10}}


def test_parent_delete_attribute_with_none(command_table):
    command_table.table[0].amplitude00.value = 1
    assert command_table.table[0].as_dict() == {
        "amplitude00": {"value": 1},
    }
    command_table.table[0].amplitude00 = None
    assert command_table.table[0].as_dict() == {}


def test_parent_property_delete_attribute_with_none(command_table):
    command_table.table[0].amplitude00.value = 1
    assert command_table.table[0].as_dict() == {
        "amplitude00": {"value": 1},
    }
    command_table.table[0].amplitude00.value = None
    assert command_table.table[0].as_dict() == {}


def test_json_non_existing_childs_ignored(command_table):
    command_table.table[0].amplitude00
    command_table.table[0].amplitude00.value
    command_table.table[0]
    command_table.header
    command_table.header.userString
    assert command_table.as_dict() == {
        "header": {"version": "1.1.0"},
        "table": [],
    }


def test_parent_clear(command_table):
    command_table.table[0].amplitude00.value = 1
    command_table.table[0].waveform.index = 10
    command_table.table[0].clear()
    assert command_table.table[0].as_dict() == {}


def test_list_entry_delete(command_table):
    command_table.table[2].amplitude00.value = 1
    del command_table.table[2]
    assert command_table.as_dict()["table"] == []


def test_test_entry_list_get_range(command_table):
    assert command_table.table.range == (0, 1024)


def test_maximum_items_in_table(command_table):
    idx = command_table.table.range[1] + 1
    with pytest.raises(ValidationError):
        command_table.table[idx]


@pytest.mark.parametrize("value", ["bar", 1, 1.2, []])
def test_derefence_json(value):
    with pytest.raises(ValueError):
        _derefence_json(value)


def test_minimum_items_in_table(command_table):
    idx = command_table.table.range[0] - 1
    with pytest.raises(ValidationError):
        command_table.table[idx]


def test_table_property_validation_error(command_table):
    with pytest.raises(ValidationError):
        command_table.table[0].amplitude00.value = 99999
