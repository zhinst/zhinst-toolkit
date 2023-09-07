from unittest.mock import patch

import pytest


@pytest.fixture()
def scope(shfqa):
    yield shfqa.scopes[0]


def test_run(mock_connection, scope):
    node = "/dev1234/scopes/0/enable"

    # already enabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    scope.run()
    mock_connection.return_value.set.assert_called_with(node, True)
    # never disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    with pytest.raises(TimeoutError) as e_info:
        scope.run(timeout=0.5)


def test_stop(mock_connection, scope):
    node = "/dev1234/scopes/0/enable"

    # already disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    scope.stop()
    mock_connection.return_value.set.assert_called_with(node, False)
    # never disabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        scope.stop(timeout=0.5)


def test_wait_done(mock_connection, scope):
    node = "/dev1234/scopes/0/enable"

    # already disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    scope.wait_done()
    # never disabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        scope.wait_done(timeout=0.5)


def test_configure(mock_connection, scope):
    with patch("zhinst.toolkit.driver.nodes.shfqa_scope.utils", autospec=True) as utils:
        scope.configure(
            input_select=scope.available_inputs[0],
            num_samples=10,
            trigger_input=scope.available_trigger_inputs[0],
        )
        utils.get_scope_settings.assert_called_with(
            "DEV1234",
            input_select=scope.available_inputs[0],
            num_samples=10,
            trigger_input=scope.available_trigger_inputs[0],
            num_segments=1,
            num_averages=1,
            trigger_delay=0,
        )
        scope.configure(
            input_select=scope.available_inputs[0],
            num_samples=10,
            trigger_input=scope.available_trigger_inputs[0],
            num_segments=0,
            num_averages=10,
            trigger_delay=33,
        )
        utils.get_scope_settings.assert_called_with(
            "DEV1234",
            input_select=scope.available_inputs[0],
            num_samples=10,
            trigger_input=scope.available_trigger_inputs[0],
            num_segments=0,
            num_averages=10,
            trigger_delay=33,
        )


def test_read(mock_connection, scope):
    with patch("zhinst.toolkit.driver.nodes.shfqa_scope.utils", autospec=True) as utils:
        utils.get_scope_data.return_value = (
            ["data1", "data2"],
            ["range1", "range2"],
            ["time1", "time2"],
        )
        recorded_data, recorded_data_range, scope_time = scope.read()
        utils.get_scope_data.assert_called_with(
            mock_connection.return_value, "DEV1234", timeout=10
        )
        assert recorded_data == ["data1", "data2"]
        assert recorded_data_range == ["range1", "range2"]
        assert scope_time == ["time1", "time2"]

        # timout argument is forwarded
        scope.read(timeout=1)
        utils.get_scope_data.assert_called_with(
            mock_connection.return_value, "DEV1234", timeout=1
        )
