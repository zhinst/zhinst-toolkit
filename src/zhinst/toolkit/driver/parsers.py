# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
import logging

import numpy as np

UHFQA_SAMPLE_RATE = 1.8e9
SHFQA_SAMPLE_RATE = 2e9
logger = logging.getLogger(__name__)


class Parse:
    """Input and output parsers for node parameters to validate and parse values."""

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
            raise TypeError(f"This value must be of type {key_type} or {value_type}")
        if value not in (list(mapping.keys()) + allowed_values):
            raise ValueError(
                f"This value must be either one of {allowed_keys} or {allowed_values}"
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
            raise TypeError(
                f"The value {value} returned from the instrument is invalid "
                f"since it is not of type {value_type}",
            )
        if value not in allowed_values:
            raise ValueError(
                f"The value {value} returned from the instrument is invalid "
                f"since it is not one of {allowed_values}",
            )
        # Extract the key corresponding to the returned value
        key = allowed_keys[allowed_values.index(value)]
        return key

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
    def greater_equal(v, limit):
        if v < limit:
            logger.warning(
                f"The value {Parse._format_number(v)} must be greater than or equal to "
                f"{Parse._format_number(limit)} and will be rounded up to: "
                f"{Parse._format_number(limit)}"
            )
            return limit
        else:
            return v

    @staticmethod
    def smaller_equal(v, limit):
        if v > limit:
            logger.warning(
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
            logger.warning(
                f"The value {Parse._format_number(v)} is not a multiple of "
                f"{Parse._format_number(factor)} and will be rounded to nearest "
                f"multiple: {Parse._format_number(v_rounded)}",
            )
            return v_rounded
        elif rounding == "down":
            v_rounded = round(v // factor) * factor
            logger.warning(
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


node_parser = {
    "SHFQA": {
        "system/clocks/referenceclock/in/status": {
            "GetParser": Parse.get_locked_status,
        },
        "scopes/0/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "scopes/0/channels/*/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "scopes/0/trigger/delay": {
            "SetParser": lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        },
        "scopes/0/length": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 16),
                lambda v: Parse.smaller_equal(v, 2 ** 18),
                lambda v: Parse.multiple_of(v, 16, "down"),
            ],
        },
        "scopes/0/segments/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "scopes/0/segments/count": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "scopes/0/averaging/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "scopes/0/averaging/count": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "qachannels/*/input/on": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "qachannels/*/output/on": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "qachannels/*/input/range": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, -50),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        },
        "qachannels/*/output/range": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, -50),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        },
        "qachannels/*/centerfreq": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 1e9),
                lambda v: Parse.smaller_equal(v, 8e9),
                lambda v: Parse.multiple_of(v, 100e6, "nearest"),
            ],
        },
        "qachannels/*/generator/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "qachannels/*/generator/delay": {
            "SetParser": lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        },
        "qachannels/*/generator/single": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "qachannels/*/readout/result/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "qachannels/*/oscs/0/gain": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, 0.0),
            ],
        },
        "qachannels/*/oscs/0/freq": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 500e6),
                lambda v: Parse.greater_equal(v, -500e6),
            ],
        },
        "qachannels/*/spectroscopy/length": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 4),
                lambda v: Parse.smaller_equal(v, ((2 ** 23) - 1) * 4),
                lambda v: Parse.multiple_of(v, 4, "down"),
            ],
        },
        "qachannels/*/spectroscopy/delay": {
            "SetParser": lambda v: Parse.multiple_of(v, 2e-9, "nearest")
        },
    },
    "SHFSG": {
        "system/clocks/referenceclock/in/status": {
            "GetParser": Parse.get_locked_status,
        },
        "system/clocks/referenceclock/out/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "system/clocks/referenceclock/out/freq": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "sgchannels/*/centerfreq": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "sgchannels/*/output/on": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "sgchannels/*/output/range": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, -30),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        },
        "sgchannels/*/output/rflfpath": {
            "GetParser": Parse.get_rf_lf,
            "SetParser": Parse.set_rf_lf,
        },
        "sgchannels/*/awg/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "sgchannels/*/awg/single": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "sgchannels/*/awg/outputs/*/enables/*": {
            "GetParser": Parse.get_true_false,
        },
        "sgchannels/*/awg/outputs/*/gains/*": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        },
        "sgchannels/*/oscs/*/freq": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 1e9),
                lambda v: Parse.greater_equal(v, -1e9),
            ],
        },
        "sgchannels/*/sines/*/phaseshift": {
            "SetParser": Parse.phase,
        },
        "sgchannels/*/sines/*/oscselect": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 0),
                lambda v: Parse.smaller_equal(v, 7),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        },
        "sgchannels/*/sines/*/harmonic": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 1),
                lambda v: Parse.smaller_equal(v, 1023),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        },
        "sgchannels/*/sines/*/i/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        },
        "sgchannels/*/sines/*/q/enable": {
            "GetParser": Parse.get_true_false,
            "SetParser": Parse.set_true_false,
        }
    },
}
