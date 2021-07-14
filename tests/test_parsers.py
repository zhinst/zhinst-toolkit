# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, strategies as st
from random import choice
import numpy as np

from .context import Parse, parser_logger

parser_logger.disable_logging()


@given(key=st.sampled_from(["on", "off"]), value=st.integers(0, 3))
def test_set_on_off(key, value):
    mapping = {"on": 1, "off": 0}
    # Randomly capitalize or lowercase each letter in the key
    # in order to test if the mapping is case-insensitive or not
    key_case_insensitive = "".join(choice((str.upper, str.lower))(c) for c in key)
    v = Parse.set_on_off(key_case_insensitive)
    assert v == mapping[key]
    if value in [0, 1]:
        v = Parse.set_on_off(value)
        v == value
    else:
        with pytest.raises(ValueError):
            Parse.set_on_off(value)
    with pytest.raises(TypeError):
        Parse.set_on_off([])
    with pytest.raises(ValueError):
        Parse.set_on_off("a;kdhf")


@given(value=st.integers(0, 3))
def test_get_on_off(value):
    mapping = {"on": 1, "off": 0}
    if value in [0, 1]:
        key = list(mapping.keys())[list(mapping.values()).index(value)]
        v = Parse.get_on_off(value)
        assert v == key
        v = Parse.get_on_off(str(value))
        assert v == key
    else:
        with pytest.raises(ValueError):
            Parse.get_on_off(value)
    with pytest.raises(ValueError):
        Parse.get_on_off("a;kdhf")


@given(
    list_keys=st.lists(elements=st.sampled_from(["on", "off"]), min_size=2, max_size=4),
    list_values=st.lists(elements=st.integers(0, 3), min_size=2, max_size=4),
    length=st.integers(2, 4),
)
def test_set_on_off_tuple_list(list_keys, list_values, length):
    mapping = {"on": 1, "off": 0}
    list_keys_case_insensitive = []
    # Randomly capitalize or lowercase each letter in the keys
    # in order to test if the mapping is case-insensitive or not
    for key in list_keys:
        list_keys_case_insensitive.append(
            "".join(choice((str.upper, str.lower))(c) for c in key)
        )
    if len(list_keys) == length:
        v = Parse.set_on_off_tuple_list(list_keys_case_insensitive, length)
        for i, value in enumerate(v):
            value == mapping[list_keys[i]]
        v = Parse.set_on_off_tuple_list(tuple(list_keys), length)
        for i, value in enumerate(v):
            value == mapping[list_keys[i]]
    else:
        with pytest.raises(ValueError):
            Parse.set_on_off_tuple_list(list_keys_case_insensitive, length)
    if max(list_values) < 2 and len(list_values) == length:
        v = Parse.set_on_off_tuple_list(list_values, length)
        for i, value in enumerate(v):
            value == list_values[i]
        v = Parse.set_on_off_tuple_list(tuple(list_values), length)
        for i, value in enumerate(v):
            value == list_values[i]
    else:
        with pytest.raises(ValueError):
            Parse.set_on_off_tuple_list(list_values, length)
    with pytest.raises(ValueError):
        Parse.set_on_off_tuple_list([], 2)
    with pytest.raises(ValueError):
        Parse.set_on_off_tuple_list(["a;kdhf", "a32r9"], 2)
    with pytest.raises(ValueError):
        Parse.set_on_off_tuple_list("a;kdhf", 2)


@given(
    list_values=st.lists(elements=st.integers(0, 3), min_size=2, max_size=4),
    length=st.integers(2, 4),
)
def test_get_on_off_tuple_list(list_values, length):
    mapping = {"on": 1, "off": 0}
    keys = []
    if max(list_values) < 2 and len(list_values) == length:
        for value in list_values:
            keys.append(list(mapping.keys())[list(mapping.values()).index(value)])
        v = Parse.get_on_off_tuple_list(list_values, length)
        assert v == tuple(keys)
        v = Parse.get_on_off_tuple_list(tuple(list_values), length)
        assert v == tuple(keys)
    else:
        with pytest.raises(ValueError):
            Parse.get_on_off_tuple_list(list_values, length)


@given(key=st.booleans(), value=st.integers(0, 3))
def test_set_true_false(key, value):
    mapping = {True: 1, False: 0}
    v = Parse.set_true_false(key)
    assert v == mapping[key]
    if value in [0, 1]:
        v = Parse.set_true_false(value)
        v == value
    else:
        with pytest.raises(ValueError):
            Parse.set_true_false(value)
    with pytest.raises(TypeError):
        Parse.set_true_false([])
    with pytest.raises(TypeError):
        Parse.set_true_false("a;kdhf")


@given(value=st.integers(0, 3))
def test_get_true_false(value):
    mapping = {True: 1, False: 0}
    if value in [0, 1]:
        key = list(mapping.keys())[list(mapping.values()).index(value)]
        v = Parse.get_true_false(value)
        assert v == key
    else:
        with pytest.raises(ValueError):
            Parse.get_true_false(value)
    with pytest.raises(ValueError):
        Parse.get_true_false("a;kdhf")


@given(key=st.sampled_from(["time", "FFT"]), value=st.integers(0, 4))
def test_set_scope_mode(key, value):
    mapping = {"time": 1, "FFT": 3}
    # Randomly capitalize or lowercase each letter in the key
    # in order to test if the mapping is case-insensitive or not
    key_case_insensitive = "".join(choice((str.upper, str.lower))(c) for c in key)
    v = Parse.set_scope_mode(key_case_insensitive)
    assert v == mapping[key]
    if value in [1, 3]:
        v = Parse.set_scope_mode(value)
        v == value
    else:
        with pytest.raises(ValueError):
            Parse.set_scope_mode(value)
        with pytest.raises(TypeError):
            Parse.set_scope_mode([])
        with pytest.raises(ValueError):
            Parse.set_scope_mode("a;kdhf")


@given(value=st.integers(0, 4))
def test_get_scope_mode(value):
    mapping = {"time": 1, "FFT": 3}
    if value in [1, 3]:
        key = list(mapping.keys())[list(mapping.values()).index(value)]
        v = Parse.get_scope_mode(value)
        assert v == key
        v = Parse.get_scope_mode(str(value))
        assert v == key
    else:
        with pytest.raises(ValueError):
            Parse.get_scope_mode(value)
    with pytest.raises(ValueError):
        Parse.get_scope_mode("a;kdhf")


@given(value=st.integers(0, 4))
def test_get_locked_status(value):
    mapping = {"locked": 0, "error": 1, "busy": 2}
    if value < 3:
        key = list(mapping.keys())[list(mapping.values()).index(value)]
        v = Parse.get_locked_status(value)
        assert v == key
        v = Parse.get_locked_status(str(value))
        assert v == key
    else:
        with pytest.raises(ValueError):
            Parse.get_locked_status(value)
    with pytest.raises(ValueError):
        Parse.get_scope_mode("a;kdhf")


@given(v=st.integers(-720, 720))
def test_phase(v):
    assert (v + 180) % 360 - 180 == Parse.phase(v)


@given(v=st.floats(-2.0, 2.0), limit=st.floats(-2.0, 2.0))
def test_greater(v, limit):
    if v > limit:
        assert v == Parse.greater(v, limit)
    else:
        with pytest.raises(ValueError):
            Parse.greater(v, limit)


@given(v=st.floats(-2.0, 2.0), limit=st.floats(-2.0, 2.0))
def test_greater_equal(v, limit):
    if v >= limit:
        assert v == Parse.greater_equal(v, limit)
    else:
        assert limit == Parse.greater_equal(v, limit)


@given(v=st.floats(-2.0, 2.0), limit=st.floats(-2.0, 2.0))
def test_smaller(v, limit):
    if v < limit:
        assert v == Parse.smaller(v, limit)
    else:
        with pytest.raises(ValueError):
            Parse.smaller(v, limit)


@given(v=st.floats(-2.0, 2.0), limit=st.floats(-2.0, 2.0))
def test_smaller_equal(v, limit):
    if v <= limit:
        assert v == Parse.smaller_equal(v, limit)
    else:
        assert limit == Parse.smaller_equal(v, limit)


@given(
    v=st.floats(-2.0, 2.0),
    factor=st.floats(1e-9, 2.0),
    rounding=st.sampled_from(["nearest", "down"]),
)
def test_multiple_of(v, factor, rounding):
    if abs(round(v / factor) * factor - v) < 1e-12:
        assert v == Parse.multiple_of(v, factor, rounding)
    else:
        if rounding == "nearest":
            v_rounded = round(v / factor) * factor
        elif rounding == "down":
            v_rounded = round(v // factor) * factor
        assert v_rounded == Parse.multiple_of(v, factor, rounding)


@given(st.integers(-180, 179))
def test_complex2deg_and_back(deg):
    complex = Parse.deg2complex(deg)
    d = Parse.complex2deg(complex)
    assert abs(d - deg) < 1e-5


@given(s=st.integers(1, (2 ** 23) - 1))
def test_uhfqa_samples2time_and_back(s):
    time = Parse.uhfqa_samples2time(4 * s)
    samples = Parse.uhfqa_time2samples(time)
    assert 4 * s == samples


@given(s=st.integers(1, (2 ** 23) - 1))
def test_shfqa_samples2time_and_back(s):
    time = Parse.shfqa_samples2time(4 * s)
    samples = Parse.shfqa_time2samples(time)
    assert 4 * s == samples


@given(year=st.integers(0, 99), month=st.integers(1, 12), build=st.integers(0, 99999))
def test_version_parser(year, month, build):
    # Add leading zeros to year and month number and convert to string
    year = str(year).zfill(2)
    month = str(month).zfill(2)
    build = str(build)
    version = Parse.version_parser(year + month + build)
    assert version == year + "." + month + "." + build
