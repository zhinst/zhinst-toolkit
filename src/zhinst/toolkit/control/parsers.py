# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import random

from zhinst.toolkit.interface import LoggerModule

UHFQA_SAMPLE_RATE = 1.8e9
SHFQA_SAMPLE_RATE = 2e9
_logger = LoggerModule(__name__)


class Parse:
    """Input and output parsers for Parameters to validate and parse values."""

    # Define a function to format the value string
    @staticmethod
    def _format_number(n):
        if abs(n) > 1e4 or abs(n) < 1e-4:
            # Use scientific notation for
            # very large and very small numbers
            return "{:.3e}".format(n)
        else:
            return n

    # Make the mapping and the value case-insensitive if the they are strings
    @staticmethod
    def _make_mapping_case_insensitive(value, mapping):
        key_type = type(list(mapping.keys())[0])
        if isinstance(value, str) and key_type == str:
            mapping = {k.lower(): v for k, v in mapping.items()}
            value = value.lower()
        return value, mapping

    # Define a function to check if input is in allowed values
    # defined by mapping
    @staticmethod
    def _setter_validate_and_parse(value, mapping):
        allowed_keys = list(mapping.keys())
        allowed_values = list(mapping.values())
        key_type = type(allowed_keys[0])
        value_type = type(allowed_values[0])
        # Make the mapping and the value case-insensitive if the they are strings
        value, mapping = Parse._make_mapping_case_insensitive(value, mapping)
        if not isinstance(value, (key_type, value_type)):
            _logger.error(
                f"This value must be of type {key_type} or {value_type}",
                _logger.ExceptionTypes.TypeError,
            )
        if value not in (list(mapping.keys()) + allowed_values):
            _logger.error(
                f"This value must be either one of {allowed_keys} or {allowed_values}",
                _logger.ExceptionTypes.ValueError,
            )
        if isinstance(value, key_type):
            value = mapping[value]
        return value

    # Define a function to check if output is in allowed values
    # defined by mapping
    @staticmethod
    def _getter_validate_and_parse(value, mapping):
        allowed_keys = list(mapping.keys())
        allowed_values = list(mapping.values())
        value_type = type(allowed_values[0])
        if not isinstance(value, value_type):
            _logger.error(
                f"The value {value} returned from the instrument is invalid "
                f"since it is not of type {value_type}",
                _logger.ExceptionTypes.TypeError,
            )
        if value not in allowed_values:
            _logger.error(
                f"The value {value} returned from the instrument is invalid "
                f"since it is not one of {allowed_values}",
                _logger.ExceptionTypes.ValueError,
            )
        # Extract the key corresponding to the returned value
        key = allowed_keys[allowed_values.index(value)]
        return key

    @staticmethod
    def none(v):
        pass

    @staticmethod
    def set_rf_lf(value):
        mapping = {"rf": 1, "lf": 0}
        value = Parse._setter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def get_rf_lf(value):
        value = int(value)
        mapping = {"rf": 1, "lf": 0}
        value = Parse._getter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def set_on_off(value):
        mapping = {"on": 1, "off": 0}
        value = Parse._setter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def get_on_off(value):
        value = int(value)
        mapping = {"on": 1, "off": 0}
        value = Parse._getter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def set_on_off_tuple_list(values, length):
        mapping = {"on": 1, "off": 0}
        random_example = tuple(random.choices(list(mapping.keys()), k=length))
        if isinstance(values, (tuple, list)) and len(values) == length:
            values = list(values)
            for i, v in enumerate(values):
                values[i] = Parse.set_on_off(v)
            values = tuple(values)
        else:
            _logger.error(
                f"The values should be specified as a tuple or list of length "
                f"{length}, e.g. {random_example}.",
                _logger.ExceptionTypes.ValueError,
            )
        return values

    @staticmethod
    def get_on_off_tuple_list(values, length):
        mapping = {"on": 1, "off": 0}
        random_example = tuple(random.choices(list(mapping.keys()), k=length))
        if isinstance(values, (tuple, list)) and len(values) == length:
            values = list(values)
            for i, v in enumerate(values):
                if isinstance(v, int) or v.isdigit():
                    values[i] = Parse.get_on_off(v)
            values = tuple(values)
        else:
            _logger.error(
                f"Invalid value is returned from the instrument as it is not specified "
                f"as a tuple or list of length {length}, e.g. {random_example}.",
                _logger.ExceptionTypes.ValueError,
            )
        return values

    @staticmethod
    def set_true_false(value):
        mapping = {True: 1, False: 0}
        value = Parse._setter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def get_true_false(value):
        value = int(value)
        mapping = {True: 1, False: 0}
        value = Parse._getter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def set_scope_mode(value):
        mapping = {"time": 1, "FFT": 3}
        value = Parse._setter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def get_scope_mode(value):
        value = int(value)
        mapping = {"time": 1, "FFT": 3}
        value = Parse._getter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def get_locked_status(value):
        value = int(value)
        mapping = {"locked": 0, "error": 1, "busy": 2}
        value = Parse._getter_validate_and_parse(value, mapping)
        return value

    @staticmethod
    def phase(v):
        return (v + 180) % 360 - 180

    @staticmethod
    def greater(v, limit):
        if v <= limit:
            _logger.error(
                f"This value must be greater than {limit}!",
                _logger.ExceptionTypes.ValueError,
            )
        return v

    @staticmethod
    def greater_equal(v, limit):
        if v < limit:
            _logger.warning(
                f"The value {Parse._format_number(v)} must be greater than or equal to "
                f"{Parse._format_number(limit)} and will be rounded up to: "
                f"{Parse._format_number(limit)}",
            )
            return limit
        else:
            return v

    @staticmethod
    def smaller(v, limit):
        if v >= limit:
            _logger.error(
                f"This value must be smaller than {limit}!",
                _logger.ExceptionTypes.ValueError,
            )
        return v

    @staticmethod
    def smaller_equal(v, limit):
        if v > limit:
            _logger.warning(
                f"The value {Parse._format_number(v)} must be smaller than or equal to "
                f"{Parse._format_number(limit)} and will be rounded down to: "
                f"{Parse._format_number(limit)}",
            )
            return limit
        else:
            return v

    @staticmethod
    def multiple_of(v, factor, rounding):
        if abs(round(v / factor) * factor - v) < 1e-12:
            return v
        elif rounding == "nearest":
            v_rounded = round(v / factor) * factor
            _logger.warning(
                f"The value {Parse._format_number(v)} is not a multiple of "
                f"{Parse._format_number(factor)} and will be rounded to nearest "
                f"multiple: {Parse._format_number(v_rounded)}",
            )
            return v_rounded
        elif rounding == "down":
            v_rounded = round(v // factor) * factor
            _logger.warning(
                f"The value {Parse._format_number(v)} is not a multiple of "
                f"{Parse._format_number(factor)} and will be rounded down to greatest "
                f"multiple: {Parse._format_number(v_rounded)}",
            )
            return v_rounded

    @staticmethod
    def deg2complex(v):
        if isinstance(v, complex):
            # Return the input without changing it, if it is already
            # a complex number
            return v
        else:
            # If it is an angle, convert it to complex number
            return np.exp(1j * np.deg2rad(v))

    @staticmethod
    def complex2deg(v):
        return np.angle(v, deg=True)

    @staticmethod
    def uhfqa_time2samples(v):
        min_samples = 4
        multiplicity_samples = 4
        min_time = min_samples / UHFQA_SAMPLE_RATE
        multiplicity_time = multiplicity_samples / UHFQA_SAMPLE_RATE
        v_rounded = Parse.greater_equal(v, min_time)
        v_rounded = Parse.multiple_of(v_rounded, multiplicity_time, "down")
        return int(round(v_rounded * UHFQA_SAMPLE_RATE))

    @staticmethod
    def uhfqa_samples2time(v):
        return v / UHFQA_SAMPLE_RATE

    @staticmethod
    def shfqa_time2samples(v):
        min_samples = 4
        max_samples = ((2 ** 23) - 1) * 4
        multiplicity_samples = 4
        min_time = min_samples / SHFQA_SAMPLE_RATE
        max_time = max_samples / SHFQA_SAMPLE_RATE
        multiplicity_time = multiplicity_samples / SHFQA_SAMPLE_RATE
        v_rounded = Parse.greater_equal(v, min_time)
        v_rounded = Parse.smaller_equal(v_rounded, max_time)
        v_rounded = Parse.multiple_of(v_rounded, multiplicity_time, "down")
        return int(round(v_rounded * SHFQA_SAMPLE_RATE))

    @staticmethod
    def shfqa_samples2time(v):
        return v / SHFQA_SAMPLE_RATE

    @staticmethod
    def version_parser(v):
        """Convert the obtained data version string to correct format"""
        v = str(v)
        year = v[:2]
        month = v[2:4]
        build = v[4:]
        return f"{year}.{month}.{build}"
