from unittest.mock import patch

import numpy as np
import pytest

from zhinst.utils.shfqa.multistate import QuditSettings


@pytest.fixture()
def multistate(shfqa):
    yield shfqa.qachannels[0].readout.multistate


def test_get_qudits_results(mock_connection, multistate):
    with patch("zhinst.toolkit.driver.nodes.multistate.utils", autospec=True) as utils:
        multistate.get_qudits_results()
        utils.get_qudits_results.assert_called_with(
            mock_connection.return_value,
            "DEV1234",
            0,
        )


def test_configure_qudit(mock_connection, multistate):
    with patch("zhinst.toolkit.driver.nodes.multistate.utils", autospec=True) as utils:
        settings = QuditSettings(
            [
                np.random.rand(400),
                np.random.rand(400),
                np.random.rand(400),
                np.random.rand(400),
            ]
        )
        utils.get_settings_transaction.return_value = [
            ("/dev1234/qachannels/0/centerfreq", 1),
            ("/dev1234/qachannels/1/centerfreq", 1),
        ]
        multistate.qudits[0].configure(settings)
        utils.get_settings_transaction.assert_called_with(
            "DEV1234", 0, 0, settings, enable=True
        )
        mock_connection.return_value.set.assert_called_with(
            utils.get_settings_transaction.return_value
        )
        # Enable = False
        multistate.qudits[0].configure(settings, enable=False)
        utils.get_settings_transaction.assert_called_with(
            "DEV1234", 0, 0, settings, enable=False
        )


def test_configure_qudit_existing_transaction(mock_connection, shfqa, multistate):
    with patch("zhinst.toolkit.driver.nodes.multistate.utils", autospec=True) as utils:
        settings = QuditSettings(
            [
                np.random.rand(400),
                np.random.rand(400),
                np.random.rand(400),
                np.random.rand(400),
            ]
        )
        utils.get_settings_transaction.return_value = [
            ("/dev1234/qachannels/0/centerfreq", 1),
            ("/dev1234/qachannels/1/centerfreq", 1),
        ]
        with shfqa.set_transaction():
            shfqa.qachannels[3].centerfreq(1, parse=False)
            multistate.qudits[0].configure(settings)
        utils.get_settings_transaction.assert_called_with(
            "DEV1234", 0, 0, settings, enable=True
        )
        mock_connection.return_value.set.assert_called_with(
            [("/dev1234/qachannels/3/centerfreq", 1)]
            + utils.get_settings_transaction.return_value
        )
