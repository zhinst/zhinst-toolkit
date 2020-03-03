import numpy as np

from .base import BaseInstrument


"""
High-level controller for MFLI.

"""


class MFLI(BaseInstrument):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "mfli", serial, **kwargs)

    def _init_settings(self):
        pass

