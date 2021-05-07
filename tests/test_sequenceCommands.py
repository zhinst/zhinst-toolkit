# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
import numpy as np

from .context import SequenceCommand, DeviceTypes, SequenceType, TriggerMode, Alignment


@given(t=st.integers(0, 3))
def test_header_comment(t):
    types = ["None", "Simple", "T1", "T2", "T2*"]
    type = types[t]
    assert type in SequenceCommand.header_comment(type)


@given(
    trigger_mode=st.sampled_from(TriggerMode),
    alignment=st.sampled_from(Alignment),
)
def test_header_info(trigger_mode, alignment):
    line = SequenceCommand.header_info(SequenceType.NONE, trigger_mode, alignment)
    assert str(trigger_mode.value) in line
    assert str(alignment.value) in line


@given(
    sequence_type=st.sampled_from(SequenceType),
    trigger_mode=st.sampled_from(TriggerMode),
    alignment=st.sampled_from(Alignment),
)
def test_replace_sequence_type(sequence_type, trigger_mode, alignment):
    default_header = SequenceCommand.header_info(
        SequenceType.NONE, trigger_mode, alignment
    )
    line = SequenceCommand.replace_sequence_type(default_header, sequence_type)
    assert str(sequence_type.value) in line


@given(i=st.integers(-1000, -1))
def test_repeat_negative(i):
    with pytest.raises(ValueError):
        SequenceCommand.repeat(i)


@given(i=st.integers(0, 1000))
def test_repeat_positive(i):
    assert str(i) in SequenceCommand.repeat(i)


def test_space():
    line = SequenceCommand.space()
    assert " " in line


def test_tab():
    line = SequenceCommand.tab()
    assert "\t" in line


@given(comment=st.text(min_size=1, max_size=100))
def test_inline_comment(comment):
    line = SequenceCommand.inline_comment(comment)
    assert str(comment) in line


@given(i=st.integers(-1000, -1))
def test_wait_negative(i):
    with pytest.raises(ValueError):
        SequenceCommand.wait(i)


@given(i=st.integers(0, 1000))
def test_wait_positive(i):
    if i == 0:
        assert SequenceCommand.wait(i) == "//\n"
    else:
        assert str(i) in SequenceCommand.wait(i)


@given(
    i=st.integers(-10, 100),
    target=st.sampled_from(
        [getattr(DeviceTypes, x) for x in ["HDAWG", "UHFQA", "UHFLI"]]
    ),
)
def test_play_zero(i, target):
    if i < 0:
        with pytest.raises(ValueError):
            SequenceCommand.play_zero(i, target)
    elif target in [DeviceTypes.HDAWG] and i < 32:
        with pytest.raises(ValueError):
            SequenceCommand.play_zero(i, target)
    elif target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI] and i < 16:
        with pytest.raises(ValueError):
            SequenceCommand.play_zero(i, target)
    else:
        SequenceCommand.play_zero(i, target)


@given(value=st.integers(-1, 2), index=st.integers(0, 3))
def test_trigger(value, index):
    if value not in [0, 1] or index not in [1, 2]:
        with pytest.raises(ValueError):
            SequenceCommand.trigger(value, index)
    else:
        SequenceCommand.trigger(value, index)


@given(length=st.integers(-10, 100))
def test_define_trigger(length):
    if length % 16 != 0 or length < 32:
        with pytest.raises(ValueError):
            SequenceCommand.define_trigger(length)
    else:
        assert str(length) in SequenceCommand.define_trigger(length)


def test_play_trigger():
    line = SequenceCommand.play_trigger()
    assert "playWave" in line
    assert "start_trigger" in line


@given(i=st.integers(0, 1000), n=st.integers(0, 1000))
def test_count_waveform(i, n):
    line = SequenceCommand.count_waveform(i, n)
    assert str(i + 1) in line
    assert str(n) in line


@given(i=st.integers(-10, 1000))
def test_assign_wave_index(i):
    if i < 0:
        with pytest.raises(ValueError):
            SequenceCommand.assign_wave_index(i)
    else:
        line = SequenceCommand.assign_wave_index(i)
        assert f"w{i + 1}" in line
        assert str(i) in line


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


@given(
    l=st.integers(-10, 100),
    i=st.integers(-1, 10),
    target=st.sampled_from(
        [getattr(DeviceTypes, x) for x in ["HDAWG", "UHFQA", "UHFLI"]]
    ),
)
def test_init_buffer_indexed(l, i, target):
    if i < 0:
        with pytest.raises(ValueError):
            SequenceCommand.init_buffer_indexed(l, i, target)
    elif target in [DeviceTypes.HDAWG] and (l % 16 or l < 32):
        with pytest.raises(ValueError):
            SequenceCommand.init_buffer_indexed(l, i, target)
    elif target in [DeviceTypes.UHFQA, DeviceTypes.UHFLI] and (l % 8 or l < 16):
        with pytest.raises(ValueError):
            SequenceCommand.init_buffer_indexed(l, i, target)
    else:
        line = SequenceCommand.init_buffer_indexed(l, i, target)
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


def test_close_bracket():
    line = SequenceCommand.close_bracket()
    assert "}" in line


@given(
    i=st.integers(-1, 5),
    target=st.sampled_from(
        [getattr(DeviceTypes, x) for x in ["HDAWG", "UHFQA", "UHFLI"]]
    ),
)
def test_wait_dig_trigger(i, target):
    if i not in [1, 2]:
        with pytest.raises(ValueError):
            SequenceCommand.wait_dig_trigger(i, target)
    else:
        SequenceCommand.wait_dig_trigger(i, target)


def test_wait_zsync_trigger():
    assert "waitZSyncTrigger" in SequenceCommand.wait_zsync_trigger()


def test_readout_trigger():
    line = SequenceCommand.readout_trigger()
    assert "startQA" in line
    assert "QA_INT_0 | QA_INT_1" in line
