import numpy as np
import pytest
from unittest.mock import patch

from zhinst.toolkit import Waveforms
from zhinst.toolkit.driver.devices.uhfqa import QAS, UHFQA, Integration
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.toolkit.nodetree import Node


@pytest.fixture()
def uhfqa(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_uhfqa.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json
    mock_connection.return_value.getString.return_value = ""

    yield UHFQA("DEV1234", "UHFQA", session)


def test_repr(uhfqa):
    assert repr(uhfqa) == "UHFQA(UHFQA,DEV1234)"


def test_qas(uhfqa):
    assert len(uhfqa.qas) == 1
    assert isinstance(uhfqa.qas[0], QAS)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(uhfqa.qas["*"], QAS)
    assert isinstance(uhfqa.qas["*"], Node)


def test_qas_integration(uhfqa):
    assert isinstance(uhfqa.qas[0].integration, Integration)
    assert isinstance(uhfqa.qas["*"].integration, Node)


def test_enable_qccs_mode(mock_connection, uhfqa):
    uhfqa.enable_qccs_mode()
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/system/extclk", "external"),
            ("/dev1234/dios/0/extclk", "internal"),
            ("/dev1234/dios/0/mode", "qa_result_qccs"),
            ("/dev1234/dios/0/drive", 3),
            ("/dev1234/awgs/0/dio/strobe/slope", "off"),
            ("/dev1234/awgs/0/dio/valid/index", 16),
            ("/dev1234/awgs/0/dio/valid/polarity", "high"),
        ]
    )
    mock_connection.reset_mock()
    with uhfqa.set_transaction():
        uhfqa.enable_qccs_mode()
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/system/extclk", "external"),
            ("/dev1234/dios/0/extclk", "internal"),
            ("/dev1234/dios/0/mode", "qa_result_qccs"),
            ("/dev1234/dios/0/drive", 3),
            ("/dev1234/awgs/0/dio/strobe/slope", "off"),
            ("/dev1234/awgs/0/dio/valid/index", 16),
            ("/dev1234/awgs/0/dio/valid/polarity", "high"),
        ]
    )


def test_adjusted_delay(uhfqa, mock_connection):

    default_delay = 0
    bypass_deskew = 0

    def get_int_side_effect(node):
        if "/dev1234/qas/0/delay" in node:
            return default_delay
        if "/dev1234/qas/0/bypass/deskew" in node:
            return bypass_deskew
        raise RuntimeError("Node not found")

    mock_connection.return_value.getInt.side_effect = get_int_side_effect

    # get value
    default_delay = 200
    assert uhfqa.qas[0].adjusted_delay() == 0
    default_delay = 300
    assert uhfqa.qas[0].adjusted_delay() == 100
    bypass_deskew = 1
    default_delay = 200
    assert uhfqa.qas[0].adjusted_delay() == 16
    default_delay = 300
    assert uhfqa.qas[0].adjusted_delay() == 116

    # set value
    bypass_deskew = 0
    assert uhfqa.qas[0].adjusted_delay(400) == 400
    mock_connection.return_value.set.assert_called_with(f"/dev1234/qas/0/delay", 600)
    bypass_deskew = 1
    assert uhfqa.qas[0].adjusted_delay(400) == 400
    mock_connection.return_value.set.assert_called_with(f"/dev1234/qas/0/delay", 584)

    with pytest.raises(ValueError):
        uhfqa.qas[0].adjusted_delay(-185)

    with pytest.raises(ValueError):
        uhfqa.qas[0].adjusted_delay(1025 - 185)


def test_qas_crosstalk_matrix(uhfqa, mock_connection):

    matrix = np.random.rand(10, 10)

    def get_double_side_effect(node):
        if "/dev1234/qas/0/crosstalk/rows/" in node:
            return matrix[int(node[-8]), int(node[-1])]
        raise RuntimeError("Node not found")

    mock_connection.return_value.getDouble.side_effect = get_double_side_effect

    # get
    result = uhfqa.qas[0].crosstalk_matrix()
    assert np.allclose(result, matrix)

    # set
    matrix2 = np.random.rand(10, 10)
    uhfqa.qas[0].crosstalk_matrix(matrix2)
    for row in range(10):
        for col in range(10):
            mock_connection.return_value.set.assert_any_call(
                f"/dev1234/qas/0/crosstalk/rows/{row}/cols/{col}", matrix2[row][col]
            )

    matrix2 = np.random.rand(11, 10)
    with pytest.raises(ValueError):
        uhfqa.qas[0].crosstalk_matrix(matrix2)


def test_awg(mock_connection, uhfqa):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    assert len(uhfqa.awgs) == 1
    assert isinstance(uhfqa.awgs[0], AWG)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(uhfqa.awgs["*"], AWG)
    assert isinstance(uhfqa.awgs["*"], Node)


def test_awg_compiler(mock_connection, uhfqa):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    with patch(
        "zhinst.toolkit.driver.nodes.awg.compile_seqc", autospec=True
    ) as compile_seqc:
        uhfqa.awgs[0].compile_sequencer_program("test")
        compile_seqc.assert_called_once_with("test", "UHFQA", "AWG,FOOBAR", 0)


class TestWriteIntegrationWeights:
    def test_write_integration_weights_waveforms(self, mock_connection, uhfqa):
        wave1 = 1.0 * np.ones(8)
        wave2 = -1.0 * np.ones(8)
        waveforms = Waveforms()
        waveforms.assign_waveform(0, wave1, wave2)
        uhfqa.qas[0].integration.write_integration_weights(waveforms)
        call_args = mock_connection.return_value.set.call_args
        assert "/dev1234/qas/0/integration/weights/0/real" == call_args[0][0][0][0]
        np.testing.assert_array_equal(wave1, call_args[0][0][0][1])
        assert "/dev1234/qas/0/integration/weights/0/imag" == call_args[0][0][1][0]
        np.testing.assert_array_equal(wave2, call_args[0][0][1][1])

    def test_write_integration_weights_waveforms_idx1(self, mock_connection, uhfqa):
        wave1 = 1.0 * np.ones(8)
        waveforms = Waveforms()
        waveforms.assign_waveform(1, wave1)
        uhfqa.qas[0].integration.write_integration_weights(waveforms)
        call_args = mock_connection.return_value.set.call_args
        assert "/dev1234/qas/0/integration/weights/1/real" == call_args[0][0][0][0]
        np.testing.assert_array_equal(wave1, call_args[0][0][0][1])

    def test_write_integration_weights_dict_complex(self, mock_connection, uhfqa):
        wave_complex = 1.0 * np.ones(8, dtype=np.complex_)
        uhfqa.qas[0].integration.write_integration_weights({0: wave_complex})
        call_args = mock_connection.return_value.set.call_args
        assert "/dev1234/qas/0/integration/weights/0/real" == call_args[0][0][0][0]
        np.testing.assert_array_equal(wave_complex.real, call_args[0][0][0][1])
        assert "/dev1234/qas/0/integration/weights/0/imag" == call_args[0][0][1][0]
        np.testing.assert_array_equal(wave_complex.imag, call_args[0][0][1][1])

    def test_write_integration_weights_dict_real(self, mock_connection, uhfqa):
        wave = 1.0 * np.ones(8)
        uhfqa.qas[0].integration.write_integration_weights({0: wave})
        call_args = mock_connection.return_value.set.call_args
        assert "/dev1234/qas/0/integration/weights/0/real" == call_args[0][0][0][0]
        np.testing.assert_array_equal(wave.real, call_args[0][0][0][1])
        assert "/dev1234/qas/0/integration/weights/0/imag" == call_args[0][0][1][0]
        np.testing.assert_array_equal(np.zeros(8), call_args[0][0][1][1])
