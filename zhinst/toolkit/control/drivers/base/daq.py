from .base import ZHTKException
from control.nodetree import Parameter


class DAQModule:
    def __init__(self, parent):
        self._parent = parent
        self._module = None

    def _setup(self):
        self._module = self._parent._controller._connection.daq_module
        # add all parameters from nodetree
        nodetree = self._module.get_nodetree("*")
        for k, v in nodetree.items():
            name = k[1:].replace("/", "_")
            setattr(self, name, Parameter(self, v, device=self))
        self._init_settings()

    def _set(self, *args):
        if self._module is None:
            raise ZHTKException("This DAQ is not connected to a dataAcquisitionModule!")
        return self._module.set(*args, device=self._parent.serial)

    def _get(self, *args, valueonly=True):
        if self._module is None:
            raise ZHTKException("This DAQ is not connected to a dataAcquisitionModule!")
        data = self._module.get(*args, device=self._parent.serial)
        return list(data.values())[0][0] if valueonly else data

    def _init_settings(self):
        self._set("preview", 1)
        self._set("historylength", 10)
        self._set("bandwidth", 0)
        self._set("hysteresis", 0.01)
        self._set("level", 0.1)
        self._set("clearhistory", 1)
        self._set("bandwidth", 0)

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
