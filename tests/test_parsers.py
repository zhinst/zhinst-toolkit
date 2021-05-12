import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import Parse


@given(st.integers(0, 5))
def test_set_on_off(n):
    map = {0: "off", 1: "on", 2: "OFF", 3: "ON", 4: 0, 5: 1}
    val = Parse.set_on_off(map[n])
    assert val in [0, 1]
    with pytest.raises(ValueError):
        Parse.set_on_off([])
    with pytest.raises(ValueError):
        Parse.set_on_off("a;kdhf")


@given(st.integers(0, 3))
def test_get_on_off(n):
    if n < 2:
        v = Parse.get_on_off(n)
        assert v in ["on", "off"]
    else:
        with pytest.raises(ValueError):
            Parse.get_on_off(n)


@given(st.integers(0, 5))
def test_set_ref_clock_wo_zsync(n):
    map = {0: "internal", 1: "external", 2: "INTERNAL", 3: "EXTERNAL", 4: 0, 5: 1}
    val = Parse.set_ref_clock_wo_zsync(map[n])
    assert val in [0, 1]
    with pytest.raises(ValueError):
        Parse.set_ref_clock_wo_zsync([])
    with pytest.raises(ValueError):
        Parse.set_ref_clock_wo_zsync("a;kdhf")


@given(st.integers(0, 3))
def test_get_ref_clock_wo_zsync(n):
    if n < 2:
        v = Parse.get_ref_clock_wo_zsync(n)
        assert v in ["internal", "external"]
    else:
        with pytest.raises(ValueError):
            Parse.get_ref_clock_wo_zsync(n)


@given(st.integers(0, 8))
def test_set_ref_clock_w_zsync(n):
    map = {
        0: "internal",
        1: "external",
        2: "zsync",
        3: "INTERNAL",
        4: "EXTERNAL",
        5: "ZSYNC",
        6: 0,
        7: 1,
        8: 2,
    }
    val = Parse.set_ref_clock_w_zsync(map[n])
    assert val in [0, 1, 2]
    with pytest.raises(ValueError):
        Parse.set_ref_clock_w_zsync([])
    with pytest.raises(ValueError):
        Parse.set_ref_clock_w_zsync("a;kdhf")


@given(st.integers(0, 4))
def test_get_ref_clock_w_zsync(n):
    if n < 3:
        v = Parse.get_ref_clock_w_zsync(n)
        assert v in ["internal", "external", "zsync"]
    else:
        with pytest.raises(ValueError):
            Parse.get_ref_clock_w_zsync(n)


@given(st.integers(0, 4))
def test_get_locked_status(n):
    if n < 3:
        v = Parse.get_locked_status(n)
        assert v in ["locked", "error", "busy"]
    else:
        with pytest.raises(ValueError):
            Parse.get_locked_status(n)


@given(st.floats(-2, 2))
def test_amp1(v):
    if abs(v) > 1:
        with pytest.raises(ValueError):
            Parse.amp1(v)
    else:
        assert abs(Parse.amp1(v)) <= 1


@given(st.integers(-180, 180))
def test_abs90(v):
    if abs(v) >= 90:
        with pytest.raises(ValueError):
            Parse.abs90(v)
    else:
        assert abs(Parse.abs90(v)) < 90


@given(st.floats(-1, 1))
def test_greater0(v):
    if v <= 0:
        with pytest.raises(ValueError):
            Parse.greater0(v)
    else:
        assert Parse.greater0(v) > 0


@given(st.floats(0.0001, 1.0))
def test_samples2time_and_back(t):
    samples = Parse.uhfqa_time2samples(t)
    time = Parse.uhfqa_samples2time(samples)
    assert abs(t - time) <= 1e-5


@given(st.integers(-180, 179))
def test_complex2deg_and_back(deg):
    complex = Parse.deg2complex(deg)
    d = Parse.complex2deg(complex)
    assert abs(d - deg) < 1e-5
