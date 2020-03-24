# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.drivers.base import BaseInstrument, DAQModule
from zhinst.toolkit.interface import DeviceTypes


"""
High-level controller for MFLI.

"""


class MFLI(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.MFLI, serial, **kwargs)
        self._daq_module = DAQModule(self)
        self._sweeper_module = SweeperModule(self)

    def connect_device(self, nodetree=True):
        super().connect_device(nodetree=nodetree)
        self.daq._setup()
        self.sweeper._setup()

    def _init_settings(self):
        pass

    @property
    def daq(self):
        return self._daq_module

    @property
    def sweeper(self):
        return self._sweeper_module
