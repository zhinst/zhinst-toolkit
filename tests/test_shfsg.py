from unittest.mock import patch

import pytest

from zhinst.toolkit.driver.devices.shfsg import AWG, Node, SGChannel


def test_repr(shfsg):
    shfsg.sgchannels["*"].configure_channel()
    assert repr(shfsg) == "SHFSG(SHFSG8,DEV1234)"


def test_sgchannels(shfsg, mock_connection):
    assert len(shfsg.sgchannels) == 8
    assert isinstance(shfsg.sgchannels[0], SGChannel)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(shfsg.sgchannels["*"], SGChannel)
    assert isinstance(shfsg.sgchannels["*"], Node)


def test_sg_awg(shfsg):
    assert isinstance(shfsg.sgchannels[0].awg, AWG)
    assert shfsg.sgchannels[0].awg.root == shfsg.root
    assert shfsg.sgchannels[0].awg.raw_tree == shfsg.raw_tree + (
        "sgchannels",
        "0",
        "awg",
    )


def test_sg_awg_compiler(mock_connection, shfsg):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    with patch(
        "zhinst.toolkit.driver.nodes.awg.compile_seqc", autospec=True
    ) as compile_seqc:
        shfsg.sgchannels[0].awg.compile_sequencer_program("test")
        compile_seqc.assert_called_once_with("test", "SHFSG8", "AWG,FOOBAR", 0)


def test_sg_awg_modulation_freq(mock_connection, shfsg, data_dir):
    mock_connection.return_value.getInt.return_value = 0
    shfsg.sgchannels[0].awg_modulation_freq()
    mock_connection.return_value.getInt.assert_called_with(
        "/dev1234/sgchannels/0/sines/0/oscselect"
    )
    mock_connection.return_value.getDouble.assert_called_with(
        "/dev1234/sgchannels/0/oscs/0/freq"
    )
    mock_connection.return_value.getInt.return_value = 1
    shfsg.sgchannels[0].awg_modulation_freq()
    mock_connection.return_value.getInt.assert_called_with(
        "/dev1234/sgchannels/0/sines/0/oscselect"
    )
    mock_connection.return_value.getDouble.assert_called_with(
        "/dev1234/sgchannels/0/oscs/1/freq"
    )


def test_awg_configure_marker_and_trigger(data_dir, mock_connection, shfsg):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfsg.sgchannels[0].awg.configure_marker_and_trigger(
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

    assert shfsg.sgchannels[0].awg.available_trigger_inputs == [
        "trigin0",
        "trigin1",
        "trigin2",
        "trigin3",
        "trigout0",
        "trigout1",
        "trigout2",
        "trigout3",
    ]

    assert shfsg.sgchannels[0].awg.available_trigger_slopes == [
        "level_sensitive",
        "rising_edge",
        "falling_edge",
        "both_edges",
    ]

    assert shfsg.sgchannels[0].awg.available_marker_outputs == [
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
        "high",
        "low",
    ]


def test_configure_channel(mock_connection, shfsg):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfsg.sgchannels[0].configure_channel(
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


def test_configure_pulse_modulation(mock_connection, shfsg):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfsg.sgchannels[0].configure_pulse_modulation(
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


def test_configure_sine_generation(mock_connection, shfsg):
    with patch("zhinst.toolkit.driver.devices.shfsg.utils", autospec=True) as utils:
        shfsg.sgchannels[0].configure_sine_generation(
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
