import json
import operator
from collections import OrderedDict
from contextlib import _GeneratorContextManager
from unittest.mock import MagicMock, Mock, patch

import pytest

from zhinst.toolkit._min_version import _MIN_DEVICE_UTILS_VERSION, _MIN_LABONE_VERSION
from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.exceptions import ToolkitError


@pytest.fixture()
def base_instrument(mock_connection, session, nodedoc_dev1234_json):
    mock_connection.return_value.listNodesJSON.return_value = nodedoc_dev1234_json
    mock_connection.return_value.getString.return_value = "OptionA"

    yield BaseInstrument("DEV1234", "test_type", session)


def test_instrument_session_property(base_instrument, session):
    assert base_instrument.session == session


def test_basic_setup(mock_connection, base_instrument):
    mock_connection.return_value.listNodesJSON.assert_called_with(
        f"/{base_instrument.serial}/*"
    )

    assert base_instrument.device_type == "test_type"
    assert base_instrument.serial == "DEV1234"
    assert repr(base_instrument) == "BaseInstrument(test_type(OptionA),DEV1234)"


def test_hf2_setup(data_dir, mock_connection, hf2_session):
    list_nodes_path = data_dir / "list_nodes_hf2_dev.txt"
    with list_nodes_path.open("r", encoding="UTF-8") as file:
        nodes_dev = file.read().split("\n")[:-1]
    mock_connection.return_value.listNodes.return_value = nodes_dev
    mock_connection.return_value.getString.return_value = "OptionA"

    instrument = BaseInstrument("DEV1234", "HF2LI", hf2_session)

    assert instrument.device_type == "HF2LI"
    assert instrument.serial == "DEV1234"
    assert repr(instrument) == "BaseInstrument(HF2LI(OptionA),DEV1234)"


def test_factory_reset_ok(base_instrument, mock_connection):
    dev_id = base_instrument.serial.lower()
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = OrderedDict(
        [
            (
                f"/{dev_id}/system/preset/error",
                {"timestamp": [0], "value": [0]},
            )
        ]
    )
    base_instrument.factory_reset()
    mock_connection.return_value.syncSetInt.assert_called_once_with(
        f"/{dev_id}/system/preset/load", 1
    )


def test_factory_reset_timeout(base_instrument, mock_connection):
    dev_id = base_instrument.serial.lower()
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        f"/{dev_id}/system/preset/busy": {"timestamp": [0], "value": [1]}
    }

    with pytest.raises(TimeoutError):
        base_instrument.factory_reset(timeout=0.00001)


def test_factory_reset_failure(base_instrument, mock_connection):
    dev_id = base_instrument.serial.lower()
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = OrderedDict(
        [
            (
                f"/{dev_id}/system/preset/error",
                {"timestamp": [0], "value": [1]},
            )
        ]
    )
    with pytest.raises(ToolkitError):
        base_instrument.factory_reset()


def test_get_streamingnodes(base_instrument):
    nodes = base_instrument.get_streamingnodes()

    assert base_instrument.dios[0].input in nodes
    assert base_instrument.scopes[0].wave in nodes
    assert base_instrument.demods[0].sample in nodes


def test_set_transaction(base_instrument):
    assert isinstance(base_instrument.set_transaction(), _GeneratorContextManager)

    base_instrument._root = Mock()
    base_instrument.set_transaction()
    base_instrument.root.set_transaction.assert_called_once()


def test_node_access(base_instrument):

    assert base_instrument.demods[0].rate == base_instrument.root.demods[0].rate
    assert base_instrument["demods"][0].rate == base_instrument.root.demods[0].rate

    assert "demods" in base_instrument
    for element in dir(base_instrument.root):
        assert element in dir(base_instrument)


def test_iter_nodetree(base_instrument):
    for res_base, res_nodetree in zip(base_instrument, base_instrument.root):
        assert res_base == res_nodetree


def test_load_preloaded_json(base_instrument, mock_connection, data_dir):

    assert base_instrument._load_preloaded_json(data_dir) is None

    mock_connection.return_value.listNodes.side_effect = [["/dev1234/stats/0/temp"]]
    return_value = base_instrument._load_preloaded_json(
        data_dir / "preloadable_nodetree.json"
    )
    assert len(return_value) == 1
    assert "/dev1234/stats/0/temp" in return_value

    mock_connection.return_value.listNodes.side_effect = [["/dev1234/stats/0/test"]]
    return_value = base_instrument._load_preloaded_json(
        data_dir / "preloadable_nodetree.json"
    )
    assert len(return_value) == 0


def test_check_python_versions():
    sub = lambda x, y: tuple(map(operator.sub, x, y))
    add = lambda x, y: tuple(map(operator.add, x, y))

    labone = BaseInstrument._version_string_to_tuple(_MIN_LABONE_VERSION)
    device_utils = BaseInstrument._version_string_to_tuple(_MIN_DEVICE_UTILS_VERSION)

    # matching version
    BaseInstrument._check_python_versions(labone, device_utils)
    # zhinst.core heigher
    BaseInstrument._check_python_versions(add(labone, (1, 0, 0)), device_utils)
    # zhinst.core lower
    with pytest.raises(ToolkitError):
        BaseInstrument._check_python_versions(sub(labone, (1, 0, 0)), device_utils)
    # utils heigher
    BaseInstrument._check_python_versions(
        labone,
        add(
            device_utils,
            (1, 0, 0),
        ),
    )
    # utils lower
    with pytest.raises(ToolkitError):
        BaseInstrument._check_python_versions(labone, sub(device_utils, (1, 0, 0)))


def test_version_string_to_tuple_new():
    test_version = BaseInstrument._version_string_to_tuple("25.1.0.2586")
    assert test_version == (25, 1, 0)


def test_version_string_to_tuple_old():
    test_version = BaseInstrument._version_string_to_tuple("25.1.2586")
    assert test_version == (25, 1, 2586)


def test_version_string_to_tuple_dev():
    test_version = BaseInstrument._version_string_to_tuple("25.1.dev2586")
    assert test_version == (25, 1, 0)


def test_version_string_to_tuple_invalid():
    test_version = BaseInstrument._version_string_to_tuple("25.1.2586.4.8.d")
    assert test_version == (25, 1, 2586)


def test_check_labone_version():

    # matching version
    BaseInstrument._check_labone_version((21, 8, 0), (21, 8, 0))
    # zhinst.core heigher
    with pytest.raises(ToolkitError):
        BaseInstrument._check_labone_version((22, 2, 0), (21, 8, 0))
    # zhinst.core lower
    with pytest.raises(ToolkitError):
        BaseInstrument._check_labone_version((21, 2, 0), (21, 8, 0))
    # patchversion missmatch
    with pytest.warns(RuntimeWarning):
        BaseInstrument._check_labone_version((21, 8, 1), (21, 8, 0))


def test_check_firmware_update_status(base_instrument, mock_connection):
    info = {
        "DEV1111": {},
        "DEV1234": {
            "AVAILABLE": 1,
            "STATUSFLAGS": 0,
        },
        "DEV1235": {},
    }
    mock_connection.return_value.getString.return_value = json.dumps(info)

    # everything ok
    base_instrument._check_firmware_update_status()

    # Upgrade available
    info = {
        "DEV1111": {},
        "DEV1234": {
            "AVAILABLE": 1,
            "STATUSFLAGS": 1 << 4,
        },
        "DEV1235": {},
    }
    mock_connection.return_value.getString.return_value = json.dumps(info)
    with pytest.raises(ToolkitError):
        base_instrument._check_firmware_update_status()
    info = {
        "DEV1111": {},
        "DEV1234": {
            "AVAILABLE": 1,
            "STATUSFLAGS": 1 << 5,
        },
        "DEV1235": {},
    }
    mock_connection.return_value.getString.return_value = json.dumps(info)
    with pytest.raises(ToolkitError):
        base_instrument._check_firmware_update_status()

    # Downgrade available
    info = {
        "DEV1111": {},
        "DEV1234": {
            "AVAILABLE": 1,
            "STATUSFLAGS": 1 << 6,
        },
        "DEV1235": {},
    }
    mock_connection.return_value.getString.return_value = json.dumps(info)
    with pytest.raises(ToolkitError):
        base_instrument._check_firmware_update_status()
    info = {
        "DEV1111": {},
        "DEV1234": {
            "AVAILABLE": 1,
            "STATUSFLAGS": 1 << 7,
        },
        "DEV1235": {},
    }
    mock_connection.return_value.getString.return_value = json.dumps(info)
    with pytest.raises(ToolkitError):
        base_instrument._check_firmware_update_status()

    # Update in progress
    info = {
        "DEV1111": {},
        "DEV1234": {
            "AVAILABLE": 1,
            "STATUSFLAGS": 1 << 8,
        },
        "DEV1235": {},
    }
    mock_connection.return_value.getString.return_value = json.dumps(info)
    with pytest.raises(ConnectionError):
        base_instrument._check_firmware_update_status()


def test_check_compatibility(base_instrument):

    with patch(
        "zhinst.toolkit.driver.devices.base.BaseInstrument._check_python_versions",
        new_callable=MagicMock,
    ) as check_python_versions:
        with patch(
            "zhinst.toolkit.driver.devices.base.BaseInstrument._check_labone_version",
            new_callable=MagicMock,
        ) as check_labone_version:
            with patch(
                "zhinst.toolkit.driver.devices.base.BaseInstrument._check_firmware_update_status",
                new_callable=MagicMock,
            ) as check_firmware_update_status:
                base_instrument.check_compatibility()
                check_python_versions.assert_called_once()
                check_labone_version.assert_called_once()
                check_firmware_update_status.assert_called_once()
