import numpy as np

from .base import BaseInstrument
from .uhfqa import AWG
from .tools import ZHTKException


"""
High-level controller for UHFQA.

"""


class UHFLI(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "uhfli", serial, **kwargs)
        self.awg = AWG(self, 0)

    def _init_settings(self):
        settings = [
            ("awgs/0/single", 1),
        ]
        self._set(settings)

    @property
    def _awg_connection(self):
        self._check_connected()
        if self.device_type not in ["hdawg", "uhfqa", "uhfli"]:
            raise ZHTKException("You cannot access AWG module of the Data Server!")
        else:
            return self._controller._connection.awg_module

