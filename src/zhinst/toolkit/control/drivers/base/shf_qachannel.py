# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .base import BaseInstrument


class SHFQAChannel:
    """Implement an SHF QAChannel representation.

    The :class:`SHFQAChannel` class implements basic functionality to
    configure QAChannel settings of the SHF instrument.

    This base class :class:`SHFQAChannel` is inherited by device-specific
    QAChannels of the SHFQA. The device-specific QAChannels add certain
    `zhinst-toolkit` :class:`Parameter` s.

    Attributes:
        parent (:class:`BaseInstrument`): The parent instrument that
            this :class:`SHFQAChannel` is associated to.
        index (int): An integer specifying the index in the parent
            instrument.

    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        self._parent = parent
        self._index = index

    def _init_qachannel_params(self):
        """Initialize parameters associated with device qachannels.

        Can be overwritten by any QAChannel that inherits from the
        :class:`SHFQAChannel`.

        """
        pass

    @property
    def parent(self):
        return self._parent

    @property
    def index(self):
        return self._index
