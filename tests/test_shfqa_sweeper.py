from dataclasses import make_dataclass
from unittest.mock import patch

import pytest

from zhinst.toolkit.driver.modules.shfqa_sweeper import SHFQASweeper, SweepConfig


@pytest.fixture()
def mock_shf_sweeper():
    with patch(
        "zhinst.toolkit.driver.modules.shfqa_sweeper.CoreSweeper", autospec=True
    ) as sweeper:
        yield sweeper


@pytest.fixture()
def mock_SweepConfig():
    with patch(
        "zhinst.toolkit.driver.modules.shfqa_sweeper.SweepConfig",
        make_dataclass("Y", fields=[("s", str, 0)]),
    ) as sweeper_config:
        yield sweeper_config


@pytest.fixture()
def mock_TriggerConfig():
    with patch(
        "zhinst.toolkit.driver.modules.shfqa_sweeper.TriggerConfig",
        make_dataclass("Y", fields=[("s", str, 0)]),
    ) as trigger_config:
        yield trigger_config


@pytest.fixture()
def sweeper_module(session, mock_shf_sweeper):
    yield SHFQASweeper(session)


def test_repr(sweeper_module):
    assert "SHFQASweeper(DataServerSession(localhost:8004))" in repr(sweeper_module)


def test_missing_node(mock_connection, mock_shf_sweeper, session):
    with patch(
        "zhinst.toolkit.driver.modules.shfqa_sweeper.SweepConfig",
        make_dataclass("Y", fields=[("s", str, 0)], bases=(SweepConfig,)),
    ) as sweeper_config:
        sweeper_module = SHFQASweeper(session)
        assert sweeper_module.sweep.s() == 0


def test_device(mock_connection, sweeper_module, session, mock_shf_sweeper):
    assert sweeper_module.device() == ""

    sweeper_module.device("dev1234")
    mock_shf_sweeper.assert_called_with(sweeper_module._daq_server, "dev1234")
    assert sweeper_module.device() == "dev1234"

    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    assert sweeper_module.device() == session.devices["dev1234"]


def test_update_settings(sweeper_module, mock_shf_sweeper):
    assert not sweeper_module.envelope.enable()
    mock_shf_sweeper.assert_called_with(sweeper_module._daq_server, "")
    # device needs to be set first
    with pytest.raises(RuntimeError) as e_info:
        sweeper_module._update_settings()

    sweeper_module.device("dev1234")
    mock_shf_sweeper.assert_called_with(sweeper_module._daq_server, "dev1234")
    sweeper_module._update_settings()
    mock_shf_sweeper.return_value.configure.assert_called_once()
    assert "sweep_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert "rf_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert "avg_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert "trig_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert "envelope_config" not in mock_shf_sweeper.return_value.configure.call_args[1]

    sweeper_module.sweep.mapping("log")
    sweeper_module.rf.output_range(1)
    sweeper_module.average.integration_time(1)
    sweeper_module.trigger.level(0.6)
    sweeper_module._update_settings()
    assert "sweep_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert (
        mock_shf_sweeper.return_value.configure.call_args[1]["sweep_config"].mapping
        == sweeper_module.sweep.mapping.node_info.enum.log.name
    )
    assert "rf_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert (
        mock_shf_sweeper.return_value.configure.call_args[1]["rf_config"].output_range
        == 1
    )
    assert "avg_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert (
        mock_shf_sweeper.return_value.configure.call_args[1][
            "avg_config"
        ].integration_time
        == 1
    )
    assert "trig_config" in mock_shf_sweeper.return_value.configure.call_args[1]
    assert (
        mock_shf_sweeper.return_value.configure.call_args[1]["trig_config"].level == 0.6
    )
    assert "envelope_config" not in mock_shf_sweeper.return_value.configure.call_args[1]

    # envelope
    sweeper_module.envelope.enable(True)
    sweeper_module._update_settings()
    envelope = mock_shf_sweeper.return_value.configure.call_args[-1]["envelope_config"]
    assert envelope.delay == 0.0


def test_update_settings_broken(
    mock_TriggerConfig,
    mock_SweepConfig,
    mock_connection,
    sweeper_module,
    mock_shf_sweeper,
    caplog,
):
    sweeper_module.device("dev1234")
    sweeper_module._update_settings()
    assert (
        "imp50 setting is no longer available in the shf_sweeper class."
        in caplog.messages
    )
    assert (
        "use_sequencer setting is no longer available in the shf_sweeper class."
        in caplog.messages
    )
    assert (
        "source setting is no longer available in the shf_sweeper class."
        in caplog.messages
    )
    assert (
        "force_sw_trigger setting is no longer available in the shf_sweeper."
        in caplog.messages
    )


def test_run(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    sweeper_module.run()
    mock_shf_sweeper.return_value.configure.assert_called_once()
    mock_shf_sweeper.return_value.run.assert_called_once()


def test_get_result(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    sweeper_module.get_result()
    mock_shf_sweeper.return_value.configure.assert_called_once()
    mock_shf_sweeper.return_value.get_result.assert_called_once()


def test_plot(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    sweeper_module.plot()
    mock_shf_sweeper.return_value.configure.assert_called_once()
    mock_shf_sweeper.return_value.plot.assert_called_once()


def test_get_offset_freq_vector(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    sweeper_module.get_offset_freq_vector()
    mock_shf_sweeper.return_value.configure.assert_called_once()
    mock_shf_sweeper.return_value.get_offset_freq_vector.assert_called_once()


def test_actual_settling_time(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    expected_value = 88.0e-9  # arbitrarily chosen floating-point value
    mock_shf_sweeper.return_value.actual_settling_time = expected_value
    assert sweeper_module.actual_settling_time() == expected_value

    with pytest.raises(AttributeError):
        sweeper_module.actual_settling_time(1)


def test_actual_hold_off_time(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    expected_value = 88.0e-9  # arbitrarily chosen floating-point value
    mock_shf_sweeper.return_value.actual_hold_off_time = expected_value
    assert sweeper_module.actual_hold_off_time() == expected_value

    with pytest.raises(AttributeError):
        sweeper_module.actual_hold_off_time(1)


def test_predicted_cycle_time(sweeper_module, mock_shf_sweeper):
    sweeper_module.device("dev1234")
    expected_value = 88.0e-9  # arbitrarily chosen floating-point value
    mock_shf_sweeper.return_value.predicted_cycle_time = expected_value
    assert sweeper_module.predicted_cycle_time() == expected_value

    with pytest.raises(AttributeError):
        sweeper_module.predicted_cycle_time(1)


def test_wildcard_get(sweeper_module, mock_shf_sweeper):
    expected_value = 88.0e-9
    mock_shf_sweeper.return_value.actual_settling_time = expected_value
    mock_shf_sweeper.return_value.actual_hold_off_time = expected_value
    mock_shf_sweeper.return_value.predicted_cycle_time = expected_value
    result = sweeper_module()

    assert (
        result[sweeper_module.actual_settling_time]
        == mock_shf_sweeper.return_value.actual_settling_time
    )
    assert (
        result[sweeper_module.actual_hold_off_time]
        == mock_shf_sweeper.return_value.actual_hold_off_time
    )
    assert (
        result[sweeper_module.predicted_cycle_time]
        == mock_shf_sweeper.return_value.predicted_cycle_time
    )
    assert result[sweeper_module.device] == ""
