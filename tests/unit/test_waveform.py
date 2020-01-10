import pytest
from hypothesis import given, assume, strategies as st

from helpers import Waveform
import numpy as np


class TestWaveform:
    def test_initial_buffer_length(self):
        w = Waveform([], [])
        assert w.buffer_length % 16 == 0
        assert w.buffer_length >= 32

    @given(st.integers(0, 100000), st.integers(0, 100000))
    def test_random_buffer_length(self, l1, l2):
        assume(l1 > 0 and l2 > 0)
        w = Waveform(np.ones(l1), np.ones(l2))
        assert w.buffer_length % 16 == 0
        assert w.buffer_length >= 32

    @given(st.integers(0, 100000), st.integers(0, 100000))
    def test_buffer_length_matches_data(self, l1, l2):
        assume(l1 > 0 and l2 > 0)
        w = Waveform(np.ones(l1), np.ones(l2))
        assert 2 * w.buffer_length == len(w.data)
        assert w.buffer_length >= 32

    @given(st.floats(0.0, 10.0))
    def test_max_range_waveform(self, amp):
        w = Waveform(amp * np.ones(8000), -amp * np.ones(8000))
        max_amp = np.max(w.data)
        min_amp = np.min(w.data)
        if abs(amp) >= 1.0:
            assert max_amp == 2 ** 15 - 1
            assert -min_amp == 2 ** 15 - 1
        else:
            assert max_amp == int(amp * (2 ** 15 - 1))
            assert min_amp == int(-amp * (2 ** 15 - 1))

    @given(st.integers(1, 10000), st.booleans())
    def test_wave_alignment(self, l, alignment):
        w = Waveform([1.0], [1.0], align_start=alignment)
        if alignment:
            assert w.data[0] == 2 ** 15 - 1
            assert w.data[1] == 2 ** 15 - 1
            assert w.data[-1] == 0
            assert w.data[-2] == 0
        else:
            assert w.data[0] == 0
            assert w.data[1] == 0
            assert w.data[-1] == 2 ** 15 - 1
            assert w.data[-2] == 2 ** 15 - 1

