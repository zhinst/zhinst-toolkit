# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.drivers.base import BaseInstrument, ZHTKException
from zhinst.toolkit.control.drivers.uhfqa import AWG


class UHFLI(BaseInstrument):
    """
    High-level controller for UHFLI. Inherits from BaseInstrument and overrides 
    the _init-settings(...) method. The property awg_connection accesses the 
    connection's awg module and is used in the AWG core as 
    awg._parent._awg_module. 
    
    Reuses the device specific AWG from the UHFQA. Might want to define a 
    device-specific AWG for the UHFLI isntead.

    """

    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "uhfli", serial, **kwargs)
        self._awg = AWG(self, 0)

    def _init_settings(self):
        settings = [
            ("awgs/0/single", 1),
        ]
        self._set(settings)

    @property
    def awg(self):
        return self._awg

    @property
    def _awg_connection(self):
        self._check_connected()
        return self._controller._connection.awg_module
