# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
from dataclasses import dataclass
import numpy as np

from .context import AWG


class Configuration:
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


class AWGMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.awg = AWG(Configuration(), "test")
        assert self.awg.id == 0
        assert self.awg._iq == True
        channels = self.awg._channels
        assert isinstance(channels, list)
        assert len(channels) == 2
        for ch in channels:
            assert ch.wave == "lafh"
            assert ch.trig == "öaklf"
            assert ch.marker == "alfhd"
        assert self.awg.parent == "test"

    @rule(p=st.text())
    def set_get_program(self, p):
        self.awg.set_program(p)
        text = self.awg.program
        if p:
            assert text == p
        else:
            assert text is None

    @rule(w=st.integers(0, 100))
    def queue_waveform(self, w):
        self.awg.waveforms.append(w)
        assert isinstance(self.awg.waveforms, list)
        assert self.awg.waveforms[-1] == w

    @rule(w=st.integers(0, 100))
    def reset_waveform(self, w):
        self.awg.waveforms.append(w)
        assert isinstance(self.awg.waveforms, list)
        assert self.awg.waveforms[-1] == w
        self.awg.reset_waveforms()
        assert isinstance(self.awg.waveforms, list)
        assert len(self.awg.waveforms) == 0


TestPrograms = AWGMachine.TestCase

