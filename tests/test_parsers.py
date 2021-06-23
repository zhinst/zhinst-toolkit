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


@given(st.integers(0, 4))
def test_get_locked_status(n):
    if n < 3:
        v = Parse.get_locked_status(n)
        assert v in ["locked", "error", "busy"]
    else:
        with pytest.raises(ValueError):
            Parse.get_locked_status(n)


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


@given(year=st.integers(0, 99), month=st.integers(1, 12), build=st.integers(0, 99999))
def test_version_parser(year, month, build):
    # Add leading zeros to year and month number and convert to string
    year = str(year).zfill(2)
    month = str(month).zfill(2)
    build = str(build)
    version = Parse.version_parser(year + month + build)
    assert version == year + "." + month + "." + build
