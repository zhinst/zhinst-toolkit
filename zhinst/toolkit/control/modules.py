# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
import json


class AWGModule:
    """
    Implements an awg module as daq.awgModule(...) in zhinst.ziPython with 
    get and set methods of the module. Allows to address different awgs on 
    different devices with the same awg module using the update(...) method. 
    """

    def __init__(self, daq):
        self._awgModule = daq.awgModule()
        self._awgModule.execute()
        self._device = self._awgModule.getString("/device")
        self._index = self._awgModule.getInt("/index")

    def set(self, *args, **kwargs):
        self.update(**kwargs)
        self._awgModule.set(*args)

    def get(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.get(*args, flat=True)

    def get_int(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.getInt(*args)

    def get_double(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.getDouble(*args)

    def get_string(self, *args, **kwargs):
        self.update(**kwargs)
        return self._awgModule.getString(*args)

    def update(self, **kwargs):
        if "device" in kwargs.keys():
            self._update_device(kwargs["device"])
        if "index" in kwargs.keys():
            self._update_index(kwargs["index"])

    def _update_device(self, device):
        if device != self.device:
            self._update_index(0)
            self._awgModule.set("/device", device)
            self._device = device

    def _update_index(self, index):
        if index != self.index:
            self._awgModule.set("/index", index)
            self._index = index

    @property
    def index(self):
        return self._index

    @property
    def device(self):
        return self._device


class DAQModule:
    def __init__(self, daq):
        self._module = daq.dataAcquisitionModule()
        self._device = self._module.getString("/device")

    def execute(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.execute()

    def finish(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.finish()

    def progress(self, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.progress()

    def trigger(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.trigger()

    def read(self, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.read()

    def subscribe(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.subscribe(*args)

    def unsubscribe(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.unsubscribe(*args)

    def save(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.save(*args)

    def clear(self, device=None):
        if device is not None:
            self.update_device(device)
        self._module.clear()

    def set(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        self._module.set(*args)

    def get(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.get(*args, flat=True)

    def get_int(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.getInt(*args)

    def get_double(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.getDouble(*args)

    def get_string(self, *args, device=None):
        if device is not None:
            self.update_device(device)
        return self._module.getString(*args)

    def get_nodetree(self, prefix, device=None, **kwargs):
        if device is not None:
            self.update_device(device)
        tree = json.loads(self._module.listNodesJSON(prefix, **kwargs))
        return tree

    def update_device(self, device):
        if device != self.device:
            self._module.set("/device", device)
            self._device = device

    @property
    def device(self):
        return self._device
