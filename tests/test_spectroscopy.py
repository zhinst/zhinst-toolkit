from unittest.mock import patch

import pytest


@pytest.fixture()
def spectroscopy(shfqa):
    yield shfqa.qachannels[0].spectroscopy


@pytest.fixture()
def m_utils():
    with patch(
        "zhinst.toolkit.driver.nodes.spectroscopy.utils", autospec=True
    ) as utils:
        yield utils


def test_configure_result_logger(mock_connection, spectroscopy, m_utils):
    spectroscopy.configure_result_logger(result_length=10)
    m_utils.get_result_logger_for_spectroscopy_settings.assert_called_with(
        "DEV1234",
        0,
        result_length=10,
        num_averages=1,
        averaging_mode=0,
    )
    spectroscopy.configure_result_logger(
        result_length=0, num_averages=2, averaging_mode=1
    )
    m_utils.get_result_logger_for_spectroscopy_settings.assert_called_with(
        "DEV1234",
        0,
        result_length=0,
        num_averages=2,
        averaging_mode=1,
    )


def test_run(mock_connection, spectroscopy, m_utils):
    spectroscopy.run()
    m_utils.enable_result_logger.assert_called_with(
        mock_connection.return_value,
        "DEV1234",
        0,
        mode="spectroscopy",
    )


def test_stop(mock_connection, spectroscopy):
    node = "/dev1234/qachannels/0/spectroscopy/result/enable"

    # already disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    spectroscopy.stop()
    mock_connection.return_value.set.assert_called_with(node, False)
    # never disabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        spectroscopy.stop(timeout=0.5)


def test_wait_done(mock_connection, spectroscopy):
    node = "/dev1234/qachannels/0/spectroscopy/result/enable"

    # already disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    spectroscopy.wait_done()
    # never disabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        spectroscopy.wait_done(timeout=0.5)


def test_read(mock_connection, spectroscopy, m_utils):
    spectroscopy.read()
    m_utils.get_result_logger_data.assert_called_with(
        mock_connection.return_value, "DEV1234", 0, mode="spectroscopy", timeout=10
    )
    spectroscopy.read(timeout=1)
    m_utils.get_result_logger_data.assert_called_with(
        mock_connection.return_value, "DEV1234", 0, mode="spectroscopy", timeout=1
    )
