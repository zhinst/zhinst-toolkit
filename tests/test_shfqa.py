from unittest.mock import patch

import pytest

from zhinst.toolkit import SHFQAChannelMode
from zhinst.toolkit.driver.devices.shfqa import Generator, QAChannel, Readout, SHFScope


def test_repr(shfqa):
    assert repr(shfqa) == "SHFQA(SHFQA4,DEV1234)"


def test_start_continuous_sw_trigger(mock_connection, shfqa):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        shfqa.start_continuous_sw_trigger(num_triggers=10, wait_time=20.0)
        utils.start_continuous_sw_trigger.assert_called_once_with(
            mock_connection.return_value, "DEV1234", num_triggers=10, wait_time=20.0
        )


def test_max_qubits_per_channel(shfqa):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        shfqa.max_qubits_per_channel
        # cached property -> second call should not call device_utils
        shfqa.max_qubits_per_channel
        utils.max_qubits_per_channel.assert_called_once()


def test_qachannels(shfqa):
    assert len(shfqa.qachannels) == 4
    assert isinstance(shfqa.qachannels[0], QAChannel)


def test_scopes(shfqa):
    assert len(shfqa.scopes) == 1
    assert isinstance(shfqa.scopes[0], SHFScope)


def test_qa_configure_channel(mock_connection, shfqa):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        shfqa.qachannels[0].configure_channel(
            input_range=10,
            output_range=20,
            center_frequency=30.0,
            mode=SHFQAChannelMode.READOUT,
        )
        utils.get_channel_settings.assert_called_once_with(
            "DEV1234",
            0,
            input_range=10,
            output_range=20,
            center_frequency=30.0,
            mode="readout",
        )


def test_qa_generator(shfqa):
    assert isinstance(shfqa.qachannels[0].generator, Generator)
    assert shfqa.qachannels[0].generator.root == shfqa.root
    assert shfqa.qachannels[0].generator.raw_tree == shfqa.raw_tree + (
        "qachannels",
        "0",
        "generator",
    )


def test_qa_generator_compiler(mock_connection, shfqa):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    with patch(
        "zhinst.toolkit.driver.nodes.awg.compile_seqc", autospec=True
    ) as compile_seqc:
        shfqa.qachannels[0].generator.compile_sequencer_program("test")
        compile_seqc.assert_called_once_with("test", "SHFQA4", "AWG,FOOBAR", 0)


def test_qa_readout(shfqa):
    assert isinstance(shfqa.qachannels[0].readout, Readout)
    assert shfqa.qachannels[0].readout.root == shfqa.root
    assert shfqa.qachannels[0].readout.raw_tree == shfqa.raw_tree + (
        "qachannels",
        "0",
        "readout",
    )
