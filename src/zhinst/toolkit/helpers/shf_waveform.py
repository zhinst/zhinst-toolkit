# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.interface import LoggerModule

_logger = LoggerModule(__name__)


class SHFWaveform(object):
    """Implements a waveform for single channel.

    The 'data' attribute holds the waveform samples with the proper
    scaling, granularity and minimal length. The 'data' attribute holds
    the actual waveform array that can be sent to the instrument.

    Arguments:
        wave (array): list or numpy array for the waveform, will be
            scaled to have a maximum amplitude of 1
        delay (float): individual waveform delay in seconds with
            respect to the time origin of the sequence, a positive
            value shifts the start of the waveform forward in time
            (default: 0).
        granularity (int): granularity that the number of samples are
            aligned to (default: 4)
        min_length (int): minimum waveform length that the number of
            samples are rounded up to (default: 4)
        align_start (bool): the waveform will be padded with zeros to
            match the granularity, either before or after the samples
            (default: True)

    Properties:
        data (array): normalized waveform data of to be uplaoded to the
            generator
        delay (double): delay in seconds of the individual waveform
            w.r.t. the sequence time origin
        buffer_length (int): number of samples for the sequence code
            buffer wave

    """

    def __init__(self, wave, delay=0, granularity=4, min_length=4, align_start=True):
        self._granularity = granularity
        self._min_length = min_length
        self._align_start = align_start
        self._wave = wave
        self._delay = delay
        self._update()

    def replace_data(self, wave, delay=0):
        """Replaces the data in the waveform."""
        self._delay = delay
        self._wave = wave
        self._update()

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
        """Update the buffer length and data attributes for new waveforms."""
        self._buffer_length = self._round_up(len(self._wave))
        self._data = self._adjust_scale(self._wave)

    def _adjust_scale(self, wave):
        """Adjust the scaling of the waveform.

        The data is actually sent as complex values in the range of
        (-1, 1).

        """
        if len(wave) == 0:
            wave = np.zeros(1)
        n = len(wave)
        n = min(n, self.buffer_length)
        m = np.max(np.abs(wave))
        data = np.zeros(self.buffer_length, dtype=np.complex)

        if self._align_start:
            if len(wave) > n:
                data[:n] = wave[:n] / m if m >= 1 else wave[:n]
            else:
                data[: len(wave)] = wave / m if m >= 1 else wave
        else:
            if len(wave) > n:
                data[:n] = (
                    wave[len(wave) - n :] / m if m >= 1 else wave[len(wave) - n :]
                )
            else:
                data[(self.buffer_length - len(wave)) :] = wave / m if m >= 1 else wave

        complex_data = data.astype(complex)
        return complex_data

    def _round_up(self, waveform_length):
        """Adapt to the allowed granularity and minimum length of
        waveforms.

        The length of the waveform is rounded up if it does not match
        the waveform granularity and minimum waveform length
        specifications of the instrument.
        """
        length = max(waveform_length, self._min_length)
        multiplier, rest = divmod(length, self._granularity)
        if not rest:
            return length
        else:
            return (multiplier + 1) * self._granularity
