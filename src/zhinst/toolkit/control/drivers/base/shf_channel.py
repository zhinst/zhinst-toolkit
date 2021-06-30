# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .base import BaseInstrument


class SHFChannel:
    """Implement an SHF Channel representation.

    The :class:`SHFChannel` class implements basic functionality to
    configure RF settings of the SHF instrument.

    This base class :class:`SHFChannel` is inherited by device-specific
    Channels for the SHFQA. The device-specific Channels add certain
    `zhinst-toolkit` :class:`Parameters`.
    """

    def __init__(self, parent: BaseInstrument, index: int) -> None:
        self._parent = parent
        self._index = index

    def _init_channel_params(self):
        """Initialize parameters associated with device channels.

        Can be overwritten by any Channel that inherits from the
        :class:`SHFChannel`.

        """
        pass
