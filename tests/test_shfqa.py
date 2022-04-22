from unittest.mock import patch

import pytest

from zhinst.toolkit import SHFQAChannelMode
from zhinst.toolkit.driver.devices.shfqa import Generator, QAChannel, Readout, SHFScope


def test_repr(shfqa):
    assert repr(shfqa) == "SHFQA(SHFQA4,DEV1234)"


def test_factory_reset(shfqa):
    # factory reset not yet implemented
    with pytest.warns(RuntimeWarning) as record:
        shfqa.factory_reset()


def test_start_continuous_sw_trigger(mock_connection, shfqa):
    with patch(
        "zhinst.toolkit.driver.devices.shfqa.deviceutils", autospec=True
    ) as deviceutils:
        shfqa.start_continuous_sw_trigger(num_triggers=10, wait_time=20.0)
        deviceutils.start_continuous_sw_trigger.assert_called_once_with(
            mock_connection.return_value, "DEV1234", num_triggers=10, wait_time=20.0
        )


def test_max_qubits_per_channel(shfqa):
    with patch(
        "zhinst.toolkit.driver.devices.shfqa.deviceutils", autospec=True
    ) as deviceutils:
        shfqa.max_qubits_per_channel
        # cached property -> second call should not call device_utils
        shfqa.max_qubits_per_channel
        deviceutils.max_qubits_per_channel.assert_called_once()


def test_qachannels(shfqa):
    assert len(shfqa.qachannels) == 4
    assert isinstance(shfqa.qachannels[0], QAChannel)


def test_scopes(shfqa):
    assert len(shfqa.scopes) == 1
    assert isinstance(shfqa.scopes[0], SHFScope)


def test_qa_configure_channel(mock_connection, shfqa):
    with patch(
        "zhinst.toolkit.driver.devices.shfqa.deviceutils", autospec=True
    ) as deviceutils:
        shfqa.qachannels[0].configure_channel(
            input_range=10,
            output_range=20,
            center_frequency=30.0,
            mode=SHFQAChannelMode.READOUT,
        )
        deviceutils.configure_channel.assert_called_once_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            input_range=10,
            output_range=20,
            center_frequency=30.0,
            mode="readout",
        )


def test_qa_generator(shfqa, data_dir, mock_connection):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    assert isinstance(shfqa.qachannels[0].generator, Generator)
    assert shfqa.qachannels[0].generator.root == shfqa.root
    assert shfqa.qachannels[0].generator.raw_tree == shfqa.raw_tree + (
        "qachannels",
        "0",
        "generator",
    )


def test_qa_readout(shfqa):
    assert isinstance(shfqa.qachannels[0].readout, Readout)
    assert shfqa.qachannels[0].readout.root == shfqa.root
    assert shfqa.qachannels[0].readout.raw_tree == shfqa.raw_tree + (
        "qachannels",
        "0",
        "readout",
    )
