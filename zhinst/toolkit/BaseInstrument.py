import numpy as np
from abc import ABC, abstractmethod

from .tools import AWGController, LIController, PQSCController, ZIDeviceConnection


"""
High-level controller for UHFQA.

"""


class BaseInstrument:
    def __init__(self, name, device_type, serial, **kwargs):
        self._name = name
        self._device_type = device_type
        self._serial = serial
        self._interface = kwargs.get("interface", "1GbE")
        if device_type in ["hdawg", "uhfqa"]:
            self._controller = AWGController(name, device_type, serial, **kwargs)
        elif device_type in ["uhfli"]:
            self._controller = LIController(name, serial, **kwargs)
        elif device_type == "pqsc":
            self._controller = PQSCController(name, serial, **kwargs)
        else:
            raise Exception("No Controller for device available!")

    def setup(self, connection: ZIDeviceConnection = None):
        self._controller.setup(connection=connection)

    def connect_device(self):
        self._controller.connect_device(
            self.name, self.device_type, self.serial, self.interface
        )
        self._init_settings()

    @property
    def name(self):
        return self._name

    @property
    def device_type(self):
        return self._device_type

    @property
    def serial(self):
        return self._serial

    @property
    def interface(self):
        return self._interface

    def _init_settings(self):
        pass

    # wrap around get and set of Controller
    def set(self, *args):
        self._controller.set(*args)

    def get(self, command, valueonly=True):
        return self._controller.get(command, valueonly=valueonly)

    def get_nodetree(self, prefix, **kwargs):
        return self._controller.get_nodetree(prefix, **kwargs)


"""
AWG Core representation.

Wrapper around AWGController with specific attributes for an AWG Core:
- a parent instrument
- an index
- a name (of the controller, e.g. "hdawg0")
- pretty __repr__() method
- wrap around controller methods with name and index for onvenience

"""


class AWGCore(ABC):
    def __init__(self, parent, name, index):
        self._parent = parent
        self._name = name
        self._index = index

    @property
    def name(self):
        return self._name + str(self._index)

    def __repr__(self):
        params = self.sequence_params["sequence_parameters"]
        s = f"{self._name}: {super().__repr__()}\n"
        s += f"    parent  : {self._parent}\n"
        s += f"    index   : {self._index}\n"
        s += f"    sequence: \n"
        s += f"           type: {self.sequence_params['sequence_type']}\n"
        for i in params.items():
            s += f"            {i}\n"
        return s

    def run(self):
        self._parent._controller.awg_run(self._index)

    def stop(self):
        self._parent._controller.awg_stop(self._index)

    def compile(self):
        self._parent._controller.awg_compile(self._index)

    def reset_queue(self):
        self._parent._controller.awg_reset_queue(self._index)

    def queue_waveform(self, wave1, wave2):
        self._parent._controller.awg_queue_waveform(self._index, data=(wave1, wave2))

    def replace_waveform(self, wave1, wave2, i=0):
        self._parent._controller.awg_replace_waveform(
            self._index, data=(wave1, wave2), index=i
        )

    def upload_waveforms(self):
        self._parent._controller.awg_upload_waveforms(self._index)

    def compile_and_upload_waveforms(self):
        self._parent._controller.awg_compile_and_upload_waveforms(self._index)

    def set_sequence_params(self, **kwargs):
        self._apply_sequence_settings(**kwargs)
        self._parent._controller.awg_set_sequence_params(self._index, **kwargs)

    @abstractmethod
    def _apply_sequence_settings(self, **kwargs):
        pass

    @property
    def is_running(self):
        return self._parent._controller.awg_is_running(self._index)

    @property
    def sequence_params(self):
        return self._parent._controller.awg_list_params(self._index)

