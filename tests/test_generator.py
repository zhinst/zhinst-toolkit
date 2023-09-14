from itertools import cycle
from unittest.mock import patch

import numpy as np
import pytest

from zhinst.toolkit import Waveforms
from zhinst.core import compile_seqc


@pytest.fixture()
def generator(data_dir, mock_connection, shfqa):
    yield shfqa.qachannels[0].generator


def test_enable_sequencer(shfqa, mock_connection):
    shfqa.qachannels[0].generator.enable_sequencer(single=True)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/qachannels/0/generator/single", 1
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/qachannels/0/generator/enable", 1
    )


def test_load_sequencer_program_empty_string_none(generator):
    with pytest.raises(RuntimeError):
        generator.load_sequencer_program("")
    with pytest.raises(RuntimeError):
        generator.load_sequencer_program(None)


def test_wait_done(mock_connection, shfqa, generator):
    single = 0
    enable = iter([])

    def get_side_effect(node, **kwargs):
        if node.lower() == "/dev1234/qachannels/0/generator/single":
            return {node: {"timestamp": [0], "value": [single]}}
        if node.lower() == "/dev1234/qachannels/0/generator/enable":
            return {node: {"timestamp": [0], "value": [next(enable)]}}
        raise RuntimeError("Node not found")

    def get_int_side_effect(node):
        return get_side_effect(node)[node]["value"][0]

    mock_connection.return_value.get.side_effect = get_side_effect
    mock_connection.return_value.getInt.side_effect = get_int_side_effect

    # if not single mode this function throws a RuntimeError
    with pytest.raises(RuntimeError) as e_info:
        shfqa.qachannels[0].generator.wait_done()

    # already finished
    single = 1
    enable = iter([0] * 2)
    shfqa.qachannels[0].generator.wait_done()
    # finishes in time
    single = 1
    enable = iter([1] * 3 + [0] * 2)
    shfqa.qachannels[0].generator.wait_done()
    # don't finish
    single = 1
    enable = cycle([1])
    with pytest.raises(TimeoutError) as e_info:
        shfqa.qachannels[0].generator.wait_done(timeout=0.1)


def test_load_sequencer_program(shfqa, generator, mock_connection):
    # everything ok
    elf, info_original = compile_seqc("setTrigger(1);", "SHFQA4", [], 0)
    info = shfqa.qachannels[0].generator.load_sequencer_program("setTrigger(1);")
    mock_connection.return_value.set.assert_called_once()
    assert (
        mock_connection.return_value.set.call_args[0][0]
        == "/dev1234/qachannels/0/generator/elf/data"
    )
    assert mock_connection.return_value.set.call_args[0][1] == elf
    assert info == info_original


def test_write_to_waveform_memory(shfqa, generator, mock_connection):

    waveforms = Waveforms()
    waveforms[0] = np.ones(1000)
    waveforms[1] = np.ones(1000, dtype=np.complex128)
    waveforms[2] = (np.ones(1000), np.ones(1000))

    waveforms_long = Waveforms()
    waveforms_long[1000] = np.zeros(1000)

    generator.write_to_waveform_memory(waveforms)
    complex_wave = np.empty(1000, dtype=np.complex128)
    complex_wave.real = np.ones(1000)
    complex_wave.imag = np.ones(1000)

    assert mock_connection.return_value.set.call_args[0][0][0] == (
        "/dev1234/qachannels/0/generator/clearwave",
        1,
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][1][0]
        == "/dev1234/qachannels/0/generator/waveforms/0/wave"
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][1][1]
        == np.ones(1000, dtype=np.complex128)
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][2][0]
        == "/dev1234/qachannels/0/generator/waveforms/1/wave"
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][2][1]
        == np.ones(1000, dtype=np.complex128)
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][3][0]
        == "/dev1234/qachannels/0/generator/waveforms/2/wave"
    )
    assert all(mock_connection.return_value.set.call_args[0][0][3][1] == complex_wave)

    shfqa.qachannels[0].generator.write_to_waveform_memory(
        waveforms, clear_existing=False
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][0][0]
        == "/dev1234/qachannels/0/generator/waveforms/0/wave"
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][0][1]
        == np.ones(1000, dtype=np.complex128)
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][1][0]
        == "/dev1234/qachannels/0/generator/waveforms/1/wave"
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][1][1]
        == np.ones(1000, dtype=np.complex128)
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][2][0]
        == "/dev1234/qachannels/0/generator/waveforms/2/wave"
    )
    assert all(mock_connection.return_value.set.call_args[0][0][2][1] == complex_wave)

    shfqa.qachannels[0].generator.write_to_waveform_memory(
        {0: np.ones(1000)}, clear_existing=True
    )
    assert mock_connection.return_value.set.call_args[0][0][0] == (
        "/dev1234/qachannels/0/generator/clearwave",
        1,
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][1][0]
        == "/dev1234/qachannels/0/generator/waveforms/0/wave"
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][1][1]
        == np.ones(1000, dtype=np.complex128)
    )

    with pytest.raises(RuntimeError) as e_info:
        shfqa.qachannels[0].generator.write_to_waveform_memory(waveforms_long)


def test_read_from_waveform_memory(shfqa, mock_connection):

    result = shfqa.qachannels[0].generator.read_from_waveform_memory()
    assert len(result) == 0
    mock_connection.return_value.get.assert_called_once_with(
        "/dev1234/qachannels/0/generator/waveforms/*/wave",
        settingsonly=False,
        flat=True,
    )

    shfqa.qachannels[0].generator.read_from_waveform_memory([0, 3])
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
    result = shfqa.qachannels[0].generator.read_from_waveform_memory()
    assert len(result) == 2
    np.allclose(result[0][0], np.ones(1000, dtype=np.complex128))
    assert not result[0][1]
    assert not result[0][2]
    np.allclose(result[1][0], np.ones(1000, dtype=np.complex128))


def test_configure_sequencer_triggering(generator, mock_connection):
    with patch("zhinst.toolkit.driver.devices.shfqa.utils", autospec=True) as utils:
        generator.configure_sequencer_triggering(
            aux_trigger="fobarob", play_pulse_delay=0.0001
        )
        utils.get_sequencer_triggering_settings.assert_called_with(
            "DEV1234",
            0,
            aux_trigger="fobarob",
            play_pulse_delay=0.0001,
        )


def test_available_aux_trigger_inputs(shfqa):
    assert shfqa.qachannels[0].generator.available_aux_trigger_inputs == [
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
