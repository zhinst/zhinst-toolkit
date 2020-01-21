import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
from dataclasses import dataclass
import numpy as np

from .context import Factory, HDAWG, UHFQA


class Device:
    def __init__(self, type):
        self.name = "test"
        self.config = DeviceConfig(type)
        self.connectivity = Connectivity()


class DeviceConfig:
    def __init__(self, type):
        self.device_type = type
        self.serial = "dev8030"
        self.interface = "1gbe"


class Connectivity:
    def __init__(self):
        self.awgs = [AWG()]
        self.dio = DIO()


class DIO:
    def __init__(self):
        self.device = None


class AWG:
    def __init__(self):
        self.awg = 0
        self.config = Config()
        self.ch0 = AWGChannel("lafh", "öaklf", "alfhd")
        self.ch1 = AWGChannel("lafh", "öaklf", "alfhd")


class Config:
    def __init__(self):
        self.iq = True


@dataclass
class AWGChannel:
    wave: str
    trig: str
    marker: str


@given(type=st.integers(0, 2))
def test_factory_type(type):
    if type == 0:
        t = "hdawg"
    if type == 1:
        t = "uhfqa"
    if type == 2:
        t = "ajf"
    dev = Device(t)

    if type == 2:
        with pytest.raises(Exception):
            d = Factory.configure_device(dev)
    else:
        d = Factory.configure_device(dev)
        if type == 0:
            assert isinstance(d, HDAWG)
        if type == 1:
            assert isinstance(d, UHFQA)
        assert d.serial == "dev8030"
        assert d.interface == "1gbe"
        awgs = d.awgs
        print(awgs)
        assert isinstance(awgs, dict)
        if type == 0:
            assert len(awgs) == 1
            assert awgs[0].id == 0
            assert awgs[0]._channels[0].wave == "lafh"
            assert awgs[0]._channels[0].trig == "öaklf"
            assert awgs[0]._channels[0].marker == "alfhd"
            assert awgs[0]._channels[1].wave == "lafh"
            assert awgs[0]._channels[1].trig == "öaklf"
            assert awgs[0]._channels[1].marker == "alfhd"
