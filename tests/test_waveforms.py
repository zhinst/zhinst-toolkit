import numpy as np
import pytest

from zhinst.toolkit.waveform import Waveforms


def test_assign():
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
    assert waveform[0] == (wave1, wave2, None)
    assert len(waveform.get_raw_vector(0)) == 1008 * 2

    # replace wave
    waveform[0] = (wave1, wave3)
    assert waveform[0] == (wave1, wave3, None)

    # replace wave
    waveform.assign_waveform(0, wave1, wave2)
    assert waveform[0] == (wave1, wave2, None)

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
    assert waveform[1] == (wave1, wave2, marker)
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

    # invalid length
    with pytest.raises(ValueError):
        waveform.get_raw_vector(0, target_length=1000)
    with pytest.raises(ValueError):
        waveform.get_raw_vector(0, target_length=2000)
