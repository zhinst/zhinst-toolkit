# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import logging
import traceback

UHFQA_SAMPLE_RATE = 1.8e9
SHFQA_SAMPLE_RATE = 2e9
logging.basicConfig(format="%(levelname)s: %(message)s")
_logger = logging.getLogger(__name__)


class Parse:
    """Input and output parsers for Parameters to validate and parse values."""

    # Define a function to return the parameter name
    @staticmethod
    def _parameter_name():
        frame_list = traceback.StackSummary.extract(traceback.walk_stack(None))
        for frame in frame_list:
            if frame.name == "<module>":
                return frame.line

    # Define a function to format the value string
    @staticmethod
    def _format_number(n):
        if abs(n) > 1e4 or abs(n) < 1e-4:
            # Use scientific notation for
            # very large and very small numbers
            return "{:.3e}".format(n)
        else:
            return n

    @staticmethod
    def none(v):
        pass

    @staticmethod
    def set_on_off(v):
        if isinstance(v, str):
            map = {"on": 1, "off": 0}
            if v.lower() not in map.keys():
                raise ValueError(f"The input value must be in {map.keys()}.")
            v = map[v.lower()]
        elif not isinstance(v, int):
            raise ValueError("This value must be either 'on' or 'off' or an integer.")
        return v

    @staticmethod
    def get_on_off(v):
        v = int(v)
        map = {1: "on", 0: "off"}
        if v not in map.keys():
            raise ValueError("Invalid value returned from the instrument!")
        return map[v]

    @staticmethod
    def set_true_false(v):
        if isinstance(v, bool):
            map = {True: 1, False: 0}
            if v not in map.keys():
                raise ValueError(f"The input value must be in {map.keys()}.")
            v = map[v]
        elif not isinstance(v, int):
            raise ValueError("This value must be either True or False or an integer.")
        return v

    @staticmethod
    def get_true_false(v):
        v = int(v)
        map = {1: True, 0: False}
        if v not in map.keys():
            raise ValueError("Invalid value returned from the instrument!")
        return map[v]

    @staticmethod
    def get_locked_status(v):
        v = int(v)
        map = {0: "locked", 1: "error", 2: "busy"}
        if v not in map.keys():
            raise ValueError("Invalid value returned from the instrument!")
        return map[v]

    @staticmethod
    def phase(v):
        return (v + 180) % 360 - 180

    @staticmethod
    def greater(v, limit):
        if v <= limit:
            raise ValueError(f"This value must be greater than {limit}!")
        return v

    @staticmethod
    def greater_equal(v, limit):
        if v < limit:
            _logger.warning(
                f"{Parse._parameter_name()}\n"
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
            raise ValueError(f"This value must be smaller than {limit}!")
        return v

    @staticmethod
    def smaller_equal(v, limit):
        if v > limit:
            _logger.warning(
                f"{Parse._parameter_name()}\n"
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
                f"{Parse._parameter_name()}\n"
                f"The value {Parse._format_number(v)} is not a multiple of "
                f"{Parse._format_number(factor)} and will be rounded to nearest "
                f"multiple: {Parse._format_number(v_rounded)}",
            )
            return v_rounded
        elif rounding == "down":
            v_rounded = round(v // factor) * factor
            _logger.warning(
                f"{Parse._parameter_name()}\n"
                f"The value {Parse._format_number(v)} is not a multiple of "
                f"{Parse._format_number(factor)} and will be rounded down to greatest "
                f"multiple: {Parse._format_number(v_rounded)}",
            )
            return v_rounded

    @staticmethod
    def deg2complex(v):
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
        """ Convert the obtained data version string to correct format"""
        v = str(v)
        year = v[:2]
        month = v[2:4]
        build = v[4:]
        return f"{year}.{month}.{build}"
