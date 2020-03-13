# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

"""
Parameter validators.
"""


class Parse:
    @staticmethod
    def none(v):
        pass

    @staticmethod
    def set_on_off(v):
        if isinstance(v, str):
            map = {"on": 1, "off": 0}
            if v.lower() not in map.keys():
                raise ValueError(f"The input value must be in {map.keys()}.")
            v = map[v]
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
    def qa_time2samples(v):
        Parse.greater0(v)
        return int(v * 1.8e9)

    @staticmethod
    def qa_samples2time(v):
        Parse.greater0(v)
        return v / 1.8e9

    @staticmethod
    def get_result_source(v):
        map = {
            0: "Crosstalk",
            1: "Threshold",
            2: "Rotation",
            4: "Crosstalk Correlation",
            5: "Threshold Correlation",
            7: "Integration",
        }
        v = int(v)
        if v not in map.keys():
            raise ValueError("Unknown value returned from the instrument!")
        return map[v]

    @staticmethod
    def set_result_source(v):
        v = v.lower()
        map = {
            "crosstalk": 0,
            "threshold": 1,
            "rotation": 2,
            "crosstalk correlation": 4,
            "threshold correlation": 5,
            "integration": 7,
        }
        if v not in map.keys():
            raise ValueError(
                f"Unknown value entered! The value must be one of {map.keys()}."
            )
        return map[v]

