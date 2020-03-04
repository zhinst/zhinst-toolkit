import numpy as np

"""
Parameter validators.
"""


def none(v):
    pass


def set_on_off(v):
    if isinstance(v, str):
        assert v.lower() in ["on", "off"]
        map = {"on": 1, "off": 0}
        v = map[v]
    return v


def get_on_off(v):

    v = int(v)
    assert v in [0, 1]
    map = {1: "on", 0: "off"}
    return map[v]


def amp1(v):
    assert abs(v) <= 1
    return v


def abs90(v):
    assert abs(v) <= 90, "This value can only be between -90 and 90."
    return v


def greater0(v):
    assert v > 0, "This value must be positive!"
    return v


def deg2complex(v):
    return np.exp(1j * np.deg2rad(v))


def complex2deg(v):
    return np.angle(v, deg=True)


def qa_time2samples(v):
    greater0(v)
    return int(v * 1.8e9)


def qa_samples2time(v):
    greater0(v)
    return v / 1.8e9

