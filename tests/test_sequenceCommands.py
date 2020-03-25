# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
import numpy as np

from .context import SequenceCommand


@given(t=st.integers(0, 3))
def test_header_comment(t):
    types = ["None", "Simple", "T1", "T2", "T2*"]
    type = types[t]
    assert type in SequenceCommand.header_comment(type)


@given(i=st.integers(-1000, -1))
def test_repeat_negative(i):
    with pytest.raises(ValueError):
        SequenceCommand.repeat(i)


@given(i=st.integers(0, 1000))
def test_repeat_positive(i):
    assert str(i) in SequenceCommand.repeat(i)


@given(i=st.integers(-1000, -1))
def test_wait_negative(i):
    with pytest.raises(ValueError):
        SequenceCommand.wait(i)


@given(i=st.integers(0, 1000))
def test_wait_positive(i):
    if i == 0:
        assert SequenceCommand.wait(i) == ""
    else:
        assert str(i) in SequenceCommand.wait(i)


@given(value=st.integers(-1, 2), index=st.integers(0, 3))
def test_trigger(value, index):
    if value not in [0, 1] or index not in [1, 2]:
        with pytest.raises(ValueError):
            SequenceCommand.trigger(value, index)
    else:
        SequenceCommand.trigger(value, index)


@given(i=st.integers(0, 1000), n=st.integers(0, 1000))
def test_count_waveform(i, n):
    line = SequenceCommand.count_waveform(i, n)
    assert str(i + 1) in line
    assert str(n) in line


@given(amp1=st.floats(-1, 1), amp2=st.floats(-1, 1))
def test_play_wave_scaled(amp1, amp2):
    line = SequenceCommand.play_wave_scaled(amp1, amp2)
    assert str(amp1) in line
    assert str(amp1) in line


@given(amp1=st.floats(-2, -1.001), amp2=st.floats(1.0001, 2))
def test_play_wave_scaled_error(amp1, amp2):
    with pytest.raises(ValueError):
        SequenceCommand.play_wave_scaled(amp1, amp2)


@given(i=st.integers(-10, 10))
def test_play_wave_indexed(i):
    if i < 0:
        with pytest.raises(ValueError):
            SequenceCommand.play_wave_indexed(i)
    else:
        assert str(i + 1) in SequenceCommand.play_wave_indexed(i)


@given(i=st.integers(-10, 10), amp=st.floats(-2, 2))
def test_play_wave_indexed_scaled(i, amp):
    if i < 0 or abs(amp) > 1:
        with pytest.raises(ValueError):
            SequenceCommand.play_wave_indexed_scaled(amp, amp, i)
    else:
        assert str(i + 1) in SequenceCommand.play_wave_indexed_scaled(amp, amp, i)
        assert str(amp) in SequenceCommand.play_wave_indexed_scaled(amp, amp, i)


@given(l=st.integers(-10, 100), i=st.integers(-1, 10))
def test_init_buffer_indexed(l, i):
    if i < 0 or l % 16 or l < 16:
        with pytest.raises(ValueError):
            SequenceCommand.init_buffer_indexed(l, i)
    else:
        line = SequenceCommand.init_buffer_indexed(l, i)
        assert str(i + 1) in line
        assert str(l) in line


@given(l=st.integers(0, 10000), p=st.integers(0, 10000), w=st.integers(0, 10000))
def test_init_gauss(l, p, w):
    if not (l > p and l > w) or l % 16 or w <= 0:
        with pytest.raises(ValueError):
            SequenceCommand.init_gauss([l, p, w])
    else:
        line = SequenceCommand.init_gauss([l, p, w])
        assert f"({l}, {p}, {w})" in line


@given(
    amp=st.floats(-2, 2),
    l=st.integers(0, 10000),
    p=st.integers(0, 10000),
    w=st.integers(0, 10000),
)
def test_init_gauss_scaled(amp, l, p, w):
    if not (l > p and l > w) or l % 16 or w <= 0 or abs(amp) > 1:
        with pytest.raises(ValueError):
            SequenceCommand.init_gauss_scaled(amp, [l, p, w])
    else:
        line = SequenceCommand.init_gauss_scaled(amp, [l, p, w])
        assert f"({l}, {p}, {w})" in line
        assert str(amp) in line


@given(i=st.integers(-1, 5))
def test_wait_trigger(i):
    if i not in [0, 1, 2]:
        with pytest.raises(ValueError):
            SequenceCommand.wait_dig_trigger(i)
    else:
        SequenceCommand.wait_dig_trigger(i)
