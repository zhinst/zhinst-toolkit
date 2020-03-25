# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.drivers.base import BaseInstrument


"""
High-level controller for MFLI.

"""


class MFLI(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "mfli", serial, **kwargs)

    def _init_settings(self):
        pass
