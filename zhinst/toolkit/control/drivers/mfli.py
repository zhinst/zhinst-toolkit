# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.control.drivers.base import BaseInstrument
from zhinst.toolkit.interface import DeviceTypes


"""
High-level controller for MFLI.

"""


class MFLI(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, DeviceTypes.MFLI, serial, **kwargs)
        self._daq_module = DAQModule(self)

    def connect_device(self, nodetree=True):
        super().connect_device(nodetree=nodetree)
        self.daq._setup()

    def _init_settings(self):
        pass

    @property
    def daq(self):
        return self._daq_module


class DAQModule:
    def __init__(self, parent):
        self._parent = parent
        self._module = None

    def _setup(self):
        self._module = self._parent._controller._connection.daq_module

    def _set(self, *args):
        self._module.set(*args, device=self._parent.serial)

    def _get(self, *args, valueonly=True):
        data = self._module.get(*args, device=self._parent.serial)
        return list(data.values())[0][0] if valueonly else data

    # here have some higher level 'measure()' mthod?? that combines subscribe read unsubscribe

    # def execute(self):
    #     self._module.execute(device=self._parent.serial)

    # def finish(self):
    #     self._module.finish(device=self._parent.serial)

    # def progress(self):
    #     return self._module.progress(device=self._parent.serial)

    # def trigger(self):
    #     self._module.trigger(device=self._parent.serial)

    # def read(self):
    #     data = self._module.read(device=self._parent.serial)
    #     # parse the data here!!!
    #     return data

    # def subscribe(self, path):
    #     self._module.subscribe(path, device=self._parent.serial)

    # def unsubscribe(self, path):
    #     self._module.unsubscribe(path, device=self._parent.serial)

    # def save(self):
    #     self._module.save(device=self._parent.serial)

