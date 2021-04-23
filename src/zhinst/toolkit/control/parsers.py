# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

UHFQA_SAMPLE_RATE = 1.8e9


class Parse:
    """Input and output parsers for Parameters to validate and parse values."""

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
    def amp1(v):
        if abs(v) > 1:
            raise ValueError(f"The given value {v} must be within -1 and +1.")
        return v

    @staticmethod
    def abs90(v):
        if abs(v) >= 90:
            raise ValueError(f"The given value {v} must be within -90 to +90.")
        return v

    @staticmethod
    def phase(v):
        return (v + 180) % 360 - 180

    @staticmethod
    def greater0(v):
        if v <= 0:
            raise ValueError("This value must be positive!")
        return v

    @staticmethod
    def deg2complex(v):
        return np.exp(1j * np.deg2rad(v))

    @staticmethod
    def complex2deg(v):
        return np.angle(v, deg=True)

    @staticmethod
    def uhfqa_time2samples(v):
        Parse.greater0(v)
        return int(round(v * UHFQA_SAMPLE_RATE))

    @staticmethod
    def uhfqa_samples2time(v):
        Parse.greater0(v)
        return v / UHFQA_SAMPLE_RATE
