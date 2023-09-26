from unittest.mock import patch

import pytest

from zhinst.toolkit import SHFQAChannelMode
from zhinst.toolkit.driver.devices.shfqa import Generator, QAChannel, Readout, SHFScope
from zhinst.toolkit.driver.devices.shfsg import AWG, Node, SGChannel


def test_repr(shfqc):
    assert repr(shfqc) == "SHFQC(SHFQC,DEV1234)"


def test_start_continuous_sw_trigger(mock_connection, shfqc):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        shfqc.start_continuous_sw_trigger(num_triggers=10, wait_time=20.0)
        utils.start_continuous_sw_trigger.assert_called_once_with(
            mock_connection.return_value, "DEV1234", num_triggers=10, wait_time=20.0
        )


def test_max_qubits_per_channel(shfqc):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        shfqc.max_qubits_per_channel
        # cached property -> second call should not call device_utils
        shfqc.max_qubits_per_channel
        utils.max_qubits_per_channel.assert_called_once()


def test_qachannels(shfqc):
    assert len(shfqc.qachannels) == 1
    assert isinstance(shfqc.qachannels[0], QAChannel)


def test_scopes(shfqc):
    assert len(shfqc.scopes) == 1
    assert isinstance(shfqc.scopes[0], SHFScope)


def test_qa_configure_channel(mock_connection, shfqc):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        shfqc.qachannels[0].configure_channel(
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


def test_qa_generator(shfqc, data_dir, mock_connection):
    assert isinstance(shfqc.qachannels[0].generator, Generator)
    assert shfqc.qachannels[0].generator.root == shfqc.root
    assert shfqc.qachannels[0].generator.raw_tree == shfqc.raw_tree + (
        "qachannels",
        "0",
        "generator",
    )


def test_qa_readout(shfqc):
    assert isinstance(shfqc.qachannels[0].readout, Readout)
    assert shfqc.qachannels[0].readout.root == shfqc.root
    assert shfqc.qachannels[0].readout.raw_tree == shfqc.raw_tree + (
        "qachannels",
        "0",
        "readout",
    )


def test_sgchannels(shfqc):
    assert len(shfqc.sgchannels) == 6
    assert isinstance(shfqc.sgchannels[0], SGChannel)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(shfqc.sgchannels["*"], SGChannel)
    assert isinstance(shfqc.sgchannels["*"], Node)


def test_sg_awg(shfqc):
    assert isinstance(shfqc.sgchannels[0].awg, AWG)
    assert shfqc.sgchannels[0].awg.root == shfqc.root
    assert shfqc.sgchannels[0].awg.raw_tree == shfqc.raw_tree + (
        "sgchannels",
        "0",
        "awg",
    )


def test_sg_awg_compiler(mock_connection, shfqc):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    with patch(
        "zhinst.toolkit.driver.nodes.awg.compile_seqc", autospec=True
    ) as compile_seqc:
        shfqc.sgchannels[0].awg.compile_sequencer_program("test")
        compile_seqc.assert_called_once_with(
            "test", "SHFQC", "AWG,FOOBAR", 0, sequencer="sg"
        )


def test_qa_awg_compiler(mock_connection, shfqc):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    with patch(
        "zhinst.toolkit.driver.nodes.awg.compile_seqc", autospec=True
    ) as compile_seqc:
        shfqc.qachannels[0].generator.compile_sequencer_program("test")
        compile_seqc.assert_called_once_with(
            "test", "SHFQC", "AWG,FOOBAR", 0, sequencer="qa"
        )


def test_sg_awg_modulation_freq(mock_connection, shfqc):
    mock_connection.return_value.getInt.return_value = 0
    shfqc.sgchannels[0].awg_modulation_freq()
    mock_connection.return_value.getInt.assert_called_with(
        "/dev1234/sgchannels/0/sines/0/oscselect"
    )
    mock_connection.return_value.getDouble.assert_called_with(
        "/dev1234/sgchannels/0/oscs/0/freq"
    )
    mock_connection.return_value.getInt.return_value = 1
    shfqc.sgchannels[0].awg_modulation_freq()
    mock_connection.return_value.getInt.assert_called_with(
        "/dev1234/sgchannels/0/sines/0/oscselect"
    )
    mock_connection.return_value.getDouble.assert_called_with(
        "/dev1234/sgchannels/0/oscs/1/freq"
    )


def test_awg_configure_marker_and_trigger(data_dir, mock_connection, shfqc):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfqc.sgchannels[0].awg.configure_marker_and_trigger(
            trigger_in_source="test1",
            trigger_in_slope="test2",
            marker_out_source="test3",
        )
        utils.get_marker_and_trigger_settings.assert_called_once_with(
            "DEV1234",
            0,
            trigger_in_source="test1",
            trigger_in_slope="test2",
            marker_out_source="test3",
        )

    assert shfqc.sgchannels[0].awg.available_trigger_inputs == [
        "trigin0",
        "trigin1",
        "trigin2",
        "trigin3",
        "trigin4",
        "trigin5",
        "trigin6",
        "trigin7",
        "inttrig",
    ]

    assert shfqc.sgchannels[0].awg.available_trigger_slopes == [
        "level_sensitive",
        "rising_edge",
        "falling_edge",
        "both_edges",
    ]

    assert shfqc.sgchannels[0].awg.available_marker_outputs == [
        "awg_trigger0",
        "awg_trigger1",
        "awg_trigger2",
        "awg_trigger3",
        "output0_marker0",
        "output0_marker1",
        "output1_marker0",
        "output1_marker1",
        "trigin0",
        "trigin1",
        "trigin2",
        "trigin3",
        "trigin4",
        "trigin5",
        "trigin6",
        "trigin7",
        "low",
        "high",
    ]


def test_configure_channel(mock_connection, shfqc):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfqc.sgchannels[0].configure_channel(
            enable=True, output_range=111, center_frequency=20.4, rf_path=False
        )
        utils.configure_channel.assert_called_once_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            enable=1,
            output_range=111,
            center_frequency=20.4,
            rflf_path=0,
        )


def test_configure_pulse_modulation(mock_connection, shfqc):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfqc.sgchannels[0].configure_pulse_modulation(
            enable=True,
            osc_index=5,
            osc_frequency=22.0,
            phase=856.6789,
            global_amp=7.0,
            gains=(3.0, -1.0, 5.0, 1.0),
            sine_generator_index=8,
        )
        utils.get_pulse_modulation_settings.assert_called_once_with(
            "DEV1234",
            0,
            enable=1,
            osc_index=5,
            osc_frequency=22.0,
            phase=856.6789,
            global_amp=7.0,
            gains=(3.0, -1.0, 5.0, 1.0),
            sine_generator_index=8,
        )


def test_configure_sine_generation(mock_connection, shfqc):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfqc.sgchannels[0].configure_sine_generation(
            enable=True,
            osc_index=5,
            osc_frequency=22.0,
            phase=856.6789,
            gains=(3.0, -1.0, 5.0, 1.0),
            sine_generator_index=8,
        )
        utils.get_sine_generation_settings.assert_called_once_with(
            "DEV1234",
            0,
            enable=1,
            osc_index=5,
            osc_frequency=22.0,
            phase=856.6789,
            gains=(3.0, -1.0, 5.0, 1.0),
            sine_generator_index=8,
        )
