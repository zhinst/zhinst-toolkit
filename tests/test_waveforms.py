import numpy as np
import pytest
import json

from zhinst.core import compile_seqc

from zhinst.toolkit.waveform import Waveforms, Wave, OutputType
from zhinst.toolkit.exceptions import ValidationError


def test_dict_behavior():
    waveform = Waveforms()
    wave1 = 1.0 * np.ones(1008)
    wave1_short = 1.0 * np.ones(500)
    wave2 = -1.0 * np.ones(1008)
    wave3 = -0.5 * np.ones(1008)
    marker = 0.0 * np.ones(1008)

    with pytest.raises(TypeError) as e_info:
        waveform[0] = 1
    with pytest.raises(RuntimeError) as e_info:
        waveform[0] = (wave1, wave2, wave3, marker)

    # "standart" waveform
    waveform[0] = (wave1, wave2)
    assert all(waveform[0][0] == wave1)
    assert all(waveform[0][1] == wave2)
    assert waveform[0][2] is None
    assert len(waveform.get_raw_vector(0)) == 1008 * 2

    # replace wave
    waveform[0] = (wave1, wave3)
    assert all(waveform[0][0] == wave1)
    assert all(waveform[0][1] == wave3)
    assert waveform[0][2] is None

    # replace wave
    waveform.assign_waveform(0, wave1, wave2)
    assert all(waveform[0][0] == wave1)
    assert all(waveform[0][1] == wave2)
    assert waveform[0][2] is None

    # delete wave
    assert 0 in waveform.keys()
    del waveform[0]
    assert 0 not in waveform.keys()

    # iter
    waveform[0] = (wave1, wave3)
    waveform[2] = (wave1, wave3)
    waveform[10] = (wave1, wave3)
    assert len(waveform) == 3
    num_elements = 0
    for _, element in waveform.items():
        assert all(element[0] == wave1)
        assert all(element[1] == wave3)
        num_elements += 1
    assert num_elements == len(waveform)

    # "standart" waveform with marker
    waveform[1] = (wave1, wave2, marker)
    assert all(waveform[1][0] == wave1)
    assert all(waveform[1][1] == wave2)
    assert all(waveform[1][2] == marker)
    assert len(waveform.get_raw_vector(1)) == 1008 * 3

    # unequal length
    with pytest.raises(RuntimeError) as e_info:
        waveform[10] = (wave1_short, wave2)
    with pytest.raises(RuntimeError) as e_info:
        waveform[10] = (wave1, wave2, wave1_short)

    # invalid inputs
    with pytest.raises(RuntimeError) as e_info:
        waveform[10] = (0, 0, 0)

    # complex values
    waveform[10] = np.ones(1008, dtype=np.complex128)
    waveform[10] = (np.ones(1008, dtype=np.complex128), marker)
    waveform[10] = (np.ones(1008, dtype=np.complex128), None, marker)
    with pytest.raises(RuntimeError) as e_info:
        waveform[10] = (np.ones(1008, dtype=np.complex128), wave2, None)


def test_get_raw_vector():
    waveform = Waveforms()
    waveform[0] = (np.ones(1008), np.ones(1008))
    waveform[1] = (np.ones(1008), np.ones(1008), np.ones(1008))
    waveform[2] = np.ones(1008, dtype=np.complex128)
    waveform[3] = (np.ones(1008, dtype=np.complex128), np.ones(1008))

    # non complex
    result0 = waveform.get_raw_vector(0)
    assert len(result0) == 2016
    result1 = waveform.get_raw_vector(1)
    assert len(result1) == 3024
    assert result0[0] == result1[0]
    assert result0[1] == result1[1]
    assert result1[2] == 1
    result2 = waveform.get_raw_vector(2)
    assert len(result2) == 2016
    assert result0[0] == result2[0]
    assert result2[1] == 0
    assert result0[2] == result2[2]
    result3 = waveform.get_raw_vector(3)
    assert len(result3) == 3024
    assert result0[0] == result3[0]
    assert result3[1] == 0
    assert result3[2] == 1

    # complex
    result0 = waveform.get_raw_vector(0, complex_output=True)
    assert len(result0) == 1008
    assert result0.dtype == np.complex128
    with pytest.warns(RuntimeWarning):
        result1 = waveform.get_raw_vector(1, complex_output=True)
    assert len(result1) == 1008
    assert all(result0 == result1)
    result2 = waveform.get_raw_vector(2, complex_output=True)
    assert all(result2 == np.ones(1008, dtype=np.complex128))
    with pytest.warns(RuntimeWarning):
        result3 = waveform.get_raw_vector(3, complex_output=True)
    assert all(result3 == np.ones(1008, dtype=np.complex128))


def test_assign():
    waveform = Waveforms()
    wave = np.ones(1008)
    waveform[0] = (wave,)
    assert all(waveform[0][0] == wave)
    waveform[1] = (wave, -wave)
    assert all(waveform[1][0] == wave)
    assert all(waveform[1][1] == -wave)
    waveform[2] = (wave, wave, -wave)
    assert all(waveform[2][0] == wave)
    assert all(waveform[2][1] == wave)
    assert all(waveform[2][2] == -wave)
    waveform[3] = (0.5 * wave, None, wave)
    assert all(waveform[3][0] == 0.5 * wave)
    assert waveform[3][1] is None
    assert all(waveform[3][2] == wave)
    waveform[4] = (np.ones(1008, dtype=np.complex128), wave)
    assert all(waveform[4][0] == np.ones(1008, dtype=np.complex128))
    assert all(waveform[4][1] == wave)
    waveform[6] = (Wave(-wave, "w1", 1), Wave(wave, "w2", 2), wave)
    assert all(waveform[6][0] == -wave)
    assert waveform[6][0].name == "w1"
    assert waveform[6][0].output == 1
    assert all(waveform[6][1] == wave)
    assert waveform[6][1].name == "w2"
    assert waveform[6][1].output == 2
    assert all(waveform[6][2] == wave)
    waveform[7] = (Wave(wave, "w", 1), wave)
    assert all(waveform[7][0] == wave)
    assert waveform[7][0].name == "w"
    assert waveform[7][0].output == 1
    assert all(waveform[2][1] == wave)
    assert waveform[7][1].name is None
    assert waveform[7][1].output is None
    assert waveform[7][2] is None
    waveform[8] = (Wave(wave, "test", 3), wave, -wave)
    assert all(waveform[8][0] == wave)
    assert waveform[8][0].name == "test"
    assert waveform[8][0].output == 3
    assert all(waveform[8][1] == wave)
    assert waveform[8][1].name is None
    assert waveform[8][1].output is None
    assert all(waveform[8][2] == -wave)


def test_sequence_snippet():
    waveform = Waveforms()
    waveform[0] = (Wave(np.ones(1008), "w1", 3), Wave(np.ones(1008), "w2", 2))
    waveform[3] = (Wave(np.ones(252), "w3"), np.ones(252), 1 * np.ones(252))
    waveform[1] = (np.ones(504), np.ones(504), 15 * np.ones(504))
    waveform[5] = (np.ones(252),)

    result = waveform.get_sequence_snippet()
    assert (
        result
        == """\
wave w1 = placeholder(1008, false, false);
wave w2 = placeholder(1008, false, false);
assignWaveIndex(1, 2, w1, 2, w2, 0);
assignWaveIndex(placeholder(504, true, true), placeholder(504, true, true), 1);
wave w3 = placeholder(252, true, false);
assignWaveIndex(w3, placeholder(252, false, false), 3);
assignWaveIndex(placeholder(252, false, false), 5);"""
    )

    waveform = Waveforms()
    waveform.assign_waveform(
        0,
        Wave(np.ones(1008), name="w1", output=OutputType.OUT1 | OutputType.OUT2),
        Wave(np.ones(1008), name="w2", output=OutputType.OUT1 | OutputType.OUT2),
        np.ones(1008),
    )
    waveform.assign_waveform(
        3,
        np.ones(1008),
        np.ones(1008),
        np.ones(1008),
    )
    waveform.assign_waveform(
        5,
        np.ones(1008),
        np.ones(1008),
    )
    waveform.assign_waveform(
        4,
        Wave(np.ones(1008), name="test1", output=OutputType.OUT2),
        Wave(np.ones(1008), name="test2", output=OutputType.OUT1),
    )
    waveform[2] = (np.ones(1008, dtype=np.complex128), None, 15 * np.ones(1008))

    waveform[1] = (
        Wave(
            np.ones(1008, dtype=np.complex128),
            name=["comp1", "comp2"],
            output=[OutputType.OUT2, OutputType.OUT1 | OutputType.OUT2],
        ),
    )

    result = waveform.get_sequence_snippet()
    assert (
        result
        == """\
wave w1 = placeholder(1008, true, false);
wave w2 = placeholder(1008, false, false);
assignWaveIndex(1, 2, w1, 1, 2, w2, 0);
wave comp1 = placeholder(1008, false, false);
wave comp2 = placeholder(1008, false, false);
assignWaveIndex(2, comp1, 1, 2, comp2, 1);
assignWaveIndex(placeholder(1008, true, true), placeholder(1008, true, true), 2);
assignWaveIndex(placeholder(1008, true, false), placeholder(1008, false, false), 3);
wave test1 = placeholder(1008, false, false);
wave test2 = placeholder(1008, false, false);
assignWaveIndex(2, test1, 1, test2, 4);
assignWaveIndex(placeholder(1008, false, false), placeholder(1008, false, false), 5);"""
    )


def test_validate_ok():
    waveform = Waveforms()
    waveform[1] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[5] = (np.ones(256),)
    seq, _ = compile_seqc(waveform.get_sequence_snippet(), "HDAWG8", "", samplerate=0.0)
    waveform.validate(seq)


def test_validate_str():
    waveform = Waveforms()
    waveform[1] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[5] = (np.ones(256),)

    info = """\
{"waveforms":[{"name":"__filler_2_4","filename":"","function":"","channels":"1","marker\
_bits":"0","length":"32","timestamp":"0000000000000000","play_config":"0"},{"name":"__p\
layWave_1_2","filename":"","function":"","channels":"2","marker_bits":"2;2","length":"5\
12","timestamp":"0000000000000000","play_config":"256884611"},{"name":"__filler_2_5\
","filename":"","function":"","channels":"1","marker_bits":"0","length":"32","timestamp\
":"0000000000000000","play_config":"0"},{"name":"__filler_2_6","filename":"","function"\
:"","channels":"1","marker_bits":"0","length":"32","timestamp":"0000000000000000","play\
_config":"0"},{"name":"__filler_2_7","filename":"","function":"","channels":"1","marker\
_bits":"0","length":"32","timestamp":"0000000000000000","play_config":"0"},{"name":"__p\
laceholder_2_3","filename":"","function":"placeholder(256, false, false)","channels":"1\
","marker_bits":"0","length":"256","timestamp":"0000000000000000","play_config":"524275\
3"}]}
"""
    waveform.validate(info)


def test_validate_dict():
    waveform = Waveforms()
    waveform[0] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[2] = (np.ones(256),)

    info = {
        "waveforms": [
            {
                "name": "__playWave_1_2",
                "filename": "",
                "function": "",
                "channels": "2",
                "marker_bits": "2;2",
                "length": "512",
                "timestamp": "0000000000000000",
                "play_config": "256884611",
            },
            {
                "name": "__filler_2_5",
                "filename": "",
                "function": "",
                "channels": "1",
                "marker_bits": "0",
                "length": "32",
                "timestamp": "0000000000000000",
                "play_config": "0",
            },
            {
                "name": "__placeholder_2_3",
                "filename": "",
                "function": "placeholder(256, false, false)",
                "channels": "1",
                "marker_bits": "0",
                "length": "256",
                "timestamp": "0000000000000000",
                "play_config": "5242753",
            },
        ]
    }
    waveform.validate(info)


def test_validate_wrong_input():
    waveform = Waveforms()
    with pytest.raises(TypeError):
        waveform.validate(None)
    with pytest.raises(TypeError):
        waveform.validate(1)
    with pytest.raises(TypeError):
        waveform.validate(("test",))
    with pytest.raises(json.decoder.JSONDecodeError):
        waveform.validate("")


def test_validate_to_many():
    waveform = Waveforms()
    waveform[1] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[5] = (np.ones(256),)
    seq, _ = compile_seqc(waveform.get_sequence_snippet(), "HDAWG8", "", samplerate=0.0)
    waveform[7] = (np.ones(256),)
    with pytest.raises(IndexError):
        waveform.validate(seq)


def test_validate_filler():
    waveform = Waveforms()
    waveform[1] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[5] = (np.ones(256),)
    seq, _ = compile_seqc(waveform.get_sequence_snippet(), "HDAWG8", "", samplerate=0.0)
    waveform[4] = (np.ones(256),)
    with pytest.raises(ValidationError):
        waveform.validate(seq)


def test_validate_wrong_type():
    waveform = Waveforms()
    waveform[0] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    seqc_str = """\
    wave w_gauss  = gauss(8000, 4000, 1000);
    assignWaveIndex(w_gauss, 0);
    """
    seq, _ = compile_seqc(seqc_str, "HDAWG8", "", samplerate=0.0)
    with pytest.raises(ValidationError):
        waveform.validate(seq)


def test_validate_to_short():
    waveform = Waveforms()
    waveform[1] = (np.ones(500), np.ones(500), 15 * np.ones(500))
    seq, _ = compile_seqc(waveform.get_sequence_snippet(), "HDAWG8", "", samplerate=0.0)
    with pytest.raises(ValidationError):
        waveform.validate(seq)


def test_validate_missing():
    waveform = Waveforms()
    waveform[1] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[4] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    waveform[5] = (np.ones(512), np.ones(512), 15 * np.ones(512))
    seq, _ = compile_seqc(waveform.get_sequence_snippet(), "HDAWG8", "", samplerate=0.0)
    del waveform[4]
    # No error by default
    waveform.validate(seq)
    # Error when enabled
    with pytest.raises(ValidationError):
        waveform.validate(seq, allow_missing=False)
