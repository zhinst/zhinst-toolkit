from itertools import cycle
from unittest.mock import patch

import numpy as np
import pytest

from zhinst.toolkit import Waveforms


@pytest.fixture()
def generator(data_dir, mock_connection, shfqa):

    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )

    yield shfqa.qachannels[0].generator


def test_enable_sequencer(generator, mock_connection):
    with patch(
        "zhinst.toolkit.driver.nodes.generator.deviceutils", autospec=True
    ) as deviceutils:
        generator.enable_sequencer(single=True)
        deviceutils.enable_sequencer.assert_called_once_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            single=1,
        )
        generator.enable_sequencer(single=False)
        deviceutils.enable_sequencer.assert_called_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            single=0,
        )


def test_load_sequencer_program_empty_string_none(generator):
    with pytest.raises(ValueError):
        generator.load_sequencer_program("")
    with pytest.raises(ValueError):
        generator.load_sequencer_program(None)


def test_wait_done(mock_connection, generator):
    single = 0
    enable = iter([])

    def get_int_side_effect(node):
        if node.upper() == "/DEV1234/QACHANNELS/0/GENERATOR/SINGLE":
            return single
        if node.upper() == "/DEV1234/QACHANNELS/0/GENERATOR/ENABLE":
            return next(enable)

    mock_connection.return_value.getInt.side_effect = get_int_side_effect

    # if not single mode this function throws a RuntimeError
    with pytest.raises(RuntimeError) as e_info:
        generator.wait_done()

    # already finished
    single = 1
    enable = iter([0] * 2)
    generator.wait_done()
    # finishes in time
    single = 1
    enable = iter([1] * 3 + [0] * 2)
    generator.wait_done()
    # don't finish
    single = 1
    enable = cycle([1])
    with pytest.raises(TimeoutError) as e_info:
        generator.wait_done(timeout=0.1)


def test_load_sequencer_program(session, generator, mock_connection):
    with patch(
        "zhinst.toolkit.driver.nodes.generator.deviceutils", autospec=True
    ) as deviceutils:
        generator.load_sequencer_program("Test")
        deviceutils.load_sequencer_program.assert_called_once_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            "Test",
            timeout=10,
        )

        generator.load_sequencer_program("Test", timeout=1)
        deviceutils.load_sequencer_program.assert_called_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            "Test",
            timeout=1,
        )


def test_write_to_waveform_memory(generator, mock_connection):

    waveforms = Waveforms()
    waveforms[0] = np.ones(1000)
    waveforms[1] = np.ones(1000, dtype=np.complex128)
    waveforms[2] = (np.ones(1000), np.ones(1000))

    waveforms_long = Waveforms()
    waveforms_long[1000] = np.zeros(1000)
    with patch(
        "zhinst.toolkit.driver.nodes.generator.deviceutils", autospec=True
    ) as deviceutils:
        generator.write_to_waveform_memory(waveforms)
        complex_wave = np.empty(1000, dtype=np.complex128)
        complex_wave.real = np.ones(1000)
        complex_wave.imag = np.ones(1000)
        complex_wave = complex_wave
        assert (
            deviceutils.write_to_waveform_memory.call_args[0][0]
            == mock_connection.return_value
        )
        assert deviceutils.write_to_waveform_memory.call_args[0][1] == "DEV1234"
        assert deviceutils.write_to_waveform_memory.call_args[0][2] == 0
        assert np.allclose(
            deviceutils.write_to_waveform_memory.call_args[0][3][1],
            np.ones(1000, dtype=np.complex128),
        )
        assert np.allclose(
            deviceutils.write_to_waveform_memory.call_args[0][3][2], complex_wave
        )
        assert (
            deviceutils.write_to_waveform_memory.call_args[1]["clear_existing"] == True
        )

        generator.write_to_waveform_memory(waveforms, clear_existing=False)
        assert (
            deviceutils.write_to_waveform_memory.call_args[1]["clear_existing"] == False
        )

        generator.write_to_waveform_memory({0: np.ones(1000)}, clear_existing=True)
        assert all(
            deviceutils.write_to_waveform_memory.call_args[0][3][0] == np.ones(1000)
        )

    with pytest.raises(RuntimeError) as e_info:
        generator.write_to_waveform_memory(waveforms_long)


def test_read_from_waveform_memory(generator, mock_connection):

    result = generator.read_from_waveform_memory()
    assert len(result) == 0
    mock_connection.return_value.get.assert_called_once_with(
        "/dev1234/qachannels/0/generator/waveforms/*/wave",
        settingsonly=False,
        flat=True,
    )

    result = generator.read_from_waveform_memory([0, 3])
    mock_connection.return_value.get.assert_called_with(
        "/dev1234/qachannels/0/generator/waveforms/0/wave,/dev1234/qachannels/0/generator/waveforms/3/wave",
        settingsonly=False,
        flat=True,
    )

    mock_connection.return_value.get.return_value = {
        "/dev1234/qachannels/0/generator/waveforms/0/wave": [
            {"vector": np.ones(1000, dtype=np.complex128)}
        ],
        "/dev1234/qachannels/0/generator/waveforms/1/wave": [
            {"vector": np.ones(1000, dtype=np.complex128)}
        ],
    }
    result = generator.read_from_waveform_memory()
    assert len(result) == 2
    np.allclose(result[0][0], np.ones(1000, dtype=np.complex128))
    assert not result[0][1]
    assert not result[0][2]
    np.allclose(result[1][0], np.ones(1000, dtype=np.complex128))


def test_configure_sequencer_triggering(generator, mock_connection):
    with patch(
        "zhinst.toolkit.driver.nodes.generator.deviceutils", autospec=True
    ) as deviceutils:
        generator.configure_sequencer_triggering(
            aux_trigger="fobarob", play_pulse_delay=0.0001
        )
        deviceutils.configure_sequencer_triggering.assert_called_with(
            mock_connection.return_value,
            "DEV1234",
            0,
            aux_trigger="fobarob",
            play_pulse_delay=0.0001,
        )


def test_available_aux_trigger_inputs(generator):
    assert generator.available_aux_trigger_inputs == [
        "chan0trigin0",
        "chan0trigin1",
        "chan1trigin0",
        "chan1trigin1",
        "chan2trigin0",
        "chan2trigin1",
        "chan3trigin0",
        "chan3trigin1",
        "chan0seqtrig0",
        "chan1seqtrig0",
        "chan2seqtrig0",
        "chan3seqtrig0",
        "chan0rod",
        "chan1rod",
        "chan2rod",
        "chan3rod",
        "swtrig0",
    ]
