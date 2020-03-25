# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.drivers.base import BaseInstrument
from zhinst.toolkit.interface import DeviceTypes


"""
High-level controller for PQSC.

"""


class PQSC(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.PQSC, serial, **kwargs)
