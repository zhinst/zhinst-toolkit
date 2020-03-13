# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np


class Waveform(object):
    def __init__(self, wave1, wave2, delay=0, granularity=16, align_start=True):
        self._granularity = granularity
        self._align_start = align_start
        self._waves = [wave1, wave2]
        self._delay = delay
        self._update()

    def add_wave(self, ch, wave):
        if ch not in [0, 1]:
            raise Exception("Waveform index out of range!")
        self._waves[ch] = wave
        self._update()

    def replace_data(self, wave1, wave2, delay=0):
        new_buffer_length = self._round_up(max(len(wave1), len(wave2), 32))
        self._delay = delay
        if new_buffer_length == self.buffer_length:
            self._waves = [wave1, wave2]
            self._update()
        else:
            raise Exception("Waveform lengths don't match!")

    @property
    def data(self):
        return self._data

    @property
    def delay(self):
        return self._delay

    @property
    def buffer_length(self):
        return self._buffer_length

    def _update(self):
        self._buffer_length = self._round_up(
            max(len(self._waves[0]), len(self._waves[1]), 32)
        )
        self._data = self._interleave_waveforms(self._waves[0], self._waves[1])

    def _interleave_waveforms(self, x1, x2):
        if len(x1) == 0:
            x1 = np.zeros(1)
        if len(x2) == 0:
            x2 = np.zeros(1)

        n = max(len(x1), len(x2))
        n = min(n, self.buffer_length)
        m1, m2 = np.max(np.abs(x1)), np.max(np.abs(x2))
        data = np.zeros((2, self.buffer_length))

        if self._align_start:
            if len(x1) > n:
                data[0, :n] = x1[:n] / m1 if m1 >= 1 else x1[:n]
            else:
                data[0, : len(x1)] = x1 / m1 if m1 >= 1 else x1
            if len(x2) > n:
                data[1, :n] = x2[:n] / m2 if m2 >= 1 else x2[:n]
            else:
                data[1, : len(x2)] = x2 / m2 if m2 >= 1 else x2
        else:
            if len(x1) > n:
                data[0, :n] = x1[len(x1) - n :] / m1 if m1 >= 1 else x1[len(x1) - n :]
            else:
                data[0, (self.buffer_length - len(x1)) :] = x1 / m1 if m1 >= 1 else x1

            if len(x2) > n:
                data[1, :n] = x2[len(x2) - n :] / m2 if m2 >= 1 else x2[len(x2) - n :]
            else:
                data[1, (self.buffer_length - len(x2)) :] = x2 / m2 if m2 >= 1 else x2

        interleaved_data = (data.reshape((-2,), order="F") * (2 ** 15 - 1)).astype(
            "int16"
        )
        return interleaved_data

    def _round_up(self, n):
        m, rest = divmod(n, self._granularity)
        return n if not rest else (m + 1) * self._granularity
