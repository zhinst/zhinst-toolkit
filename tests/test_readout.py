from unittest.mock import patch

import numpy as np
import pytest

from zhinst.toolkit.waveform import Waveforms


@pytest.fixture()
def readout(shfqa):
    yield shfqa.qachannels[0].readout


def test_configure_result_logger(mock_connection, readout):
    with patch("zhinst.toolkit.driver.nodes.readout.utils", autospec=True) as utils:
        readout.configure_result_logger(result_source="test", result_length=10)
        utils.get_result_logger_for_readout_settings.assert_called_with(
            "DEV1234",
            0,
            result_source="test",
            result_length=10,
            num_averages=1,
            averaging_mode=0,
        )
        readout.configure_result_logger(
            result_source="test2", result_length=0, num_averages=2, averaging_mode=1
        )
        utils.get_result_logger_for_readout_settings.assert_called_with(
            "DEV1234",
            0,
            result_source="test2",
            result_length=0,
            num_averages=2,
            averaging_mode=1,
        )


def test_run(mock_connection, readout):
    with patch("zhinst.toolkit.driver.nodes.readout.utils", autospec=True) as utils:
        readout.run()
        utils.enable_result_logger.assert_called_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            mode="readout",
        )


def test_stop(mock_connection, readout):
    node = "/dev1234/qachannels/0/readout/result/enable"

    # already disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    readout.stop()
    mock_connection.return_value.set.assert_called_with(node, False)
    # never disabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        readout.stop(timeout=0.5)


def test_wait_done(mock_connection, readout):
    node = "/dev1234/qachannels/0/readout/result/enable"

    # already disabled
    mock_connection.return_value.getInt.return_value = 0
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [0]}
    }
    readout.wait_done()
    # never disabled
    mock_connection.return_value.getInt.return_value = 1
    mock_connection.return_value.get.return_value = {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        readout.wait_done(timeout=0.5)


def test_read(mock_connection, readout):
    with patch("zhinst.toolkit.driver.nodes.readout.utils", autospec=True) as utils:
        readout.read()
        utils.get_result_logger_data.assert_called_with(
            mock_connection.return_value, "DEV1234", 0, mode="readout", timeout=10
        )
        readout.read(timeout=1)
        utils.get_result_logger_data.assert_called_with(
            mock_connection.return_value, "DEV1234", 0, mode="readout", timeout=1
        )


def test_write_integration_weights(mock_connection, readout):
    waveforms = Waveforms()
    waveforms[0] = np.ones(1000)
    waveforms[1] = np.ones(1000, dtype=np.complex128)
    waveforms[2] = (np.ones(1000), np.ones(1000))

    waveforms_long = Waveforms()
    waveforms_long[1000] = np.zeros(1000)
    with patch("zhinst.toolkit.driver.nodes.readout.utils", autospec=True) as utils:
        readout.write_integration_weights(waveforms)
        complex_wave = np.empty(1000, dtype=np.complex128)
        complex_wave.real = np.ones(1000)
        complex_wave.imag = np.ones(1000)
        assert (
            utils.get_configure_weighted_integration_settings.call_args[0][0]
            == "DEV1234"
        )
        assert utils.get_configure_weighted_integration_settings.call_args[0][1] == 0
        assert np.allclose(
            utils.get_configure_weighted_integration_settings.call_args[1]["weights"][
                1
            ],
            np.ones(1000, dtype=np.complex128),
        )
        assert np.allclose(
            utils.get_configure_weighted_integration_settings.call_args[1]["weights"][
                2
            ],
            complex_wave,
        )
        assert (
            utils.get_configure_weighted_integration_settings.call_args[1][
                "integration_delay"
            ]
            == 0.0
        )
        assert (
            utils.get_configure_weighted_integration_settings.call_args[1][
                "clear_existing"
            ]
            == True
        )

        readout.write_integration_weights(waveforms, integration_delay=0.5)
        assert (
            utils.get_configure_weighted_integration_settings.call_args[1][
                "integration_delay"
            ]
            == 0.5
        )

        readout.write_integration_weights(waveforms, clear_existing=False)
        assert (
            utils.get_configure_weighted_integration_settings.call_args[1][
                "clear_existing"
            ]
            == False
        )

        readout.write_integration_weights({0: np.ones(1000)}, clear_existing=True)
        assert all(
            utils.get_configure_weighted_integration_settings.call_args[1]["weights"][0]
            == np.ones(1000)
        )

    with pytest.raises(RuntimeError) as e_info:
        readout.write_integration_weights(waveforms_long)


def test_read_integration_weights(mock_connection, readout):

    result = readout.read_integration_weights()
    assert len(result) == 0
    mock_connection.return_value.get.assert_called_once_with(
        "/dev1234/qachannels/0/readout/integration/weights/*/wave",
        settingsonly=False,
        flat=True,
    )

    readout.read_integration_weights([0, 3])
    mock_connection.return_value.get.assert_called_with(
        "/dev1234/qachannels/0/readout/integration/weights/0/wave,/dev1234/qachannels/0/readout/integration/weights/3/wave",
        settingsonly=False,
        flat=True,
    )

    mock_connection.return_value.get.return_value = {
        "/dev1234/qachannels/0/readout/integration/weights/0/wave": [
            {"vector": np.ones(1000, dtype=np.complex128)}
        ],
        "/dev1234/qachannels/0/readout/integration/weights/1/wave": [
            {"vector": np.ones(1000, dtype=np.complex128)}
        ],
    }
    result = readout.read_integration_weights()
    assert len(result) == 2
    np.allclose(result[0][0], np.ones(1000, dtype=np.complex128))
    assert not result[0][1]
    assert not result[0][2]
    np.allclose(result[1][0], np.ones(1000, dtype=np.complex128))
