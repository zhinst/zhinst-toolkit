from .base import ZHTKException


class DAQModule:
    def __init__(self, parent):
        self._parent = parent
        self._module = None

    def _setup(self):
        self._module = self._parent._controller._connection.daq_module

    def _set(self, *args):
        if self._module is None:
            raise ZHTKException("This DAQ is not connected to a dataAcquisitionModule!")
        self._module.set(*args, device=self._parent.serial)

    def _get(self, *args, valueonly=True):
        if self._module is None:
            raise ZHTKException("This DAQ is not connected to a dataAcquisitionModule!")
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
