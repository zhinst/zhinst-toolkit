import numpy as np

from .BaseInstrument import BaseInstrument
from .UHFQA import AWG


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
        self.set(settings)

