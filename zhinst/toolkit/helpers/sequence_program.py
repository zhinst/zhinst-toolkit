# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import attr
from .sequences import (
    Sequence,
    SimpleSequence,
    RabiSequence,
    T1Sequence,
    T2Sequence,
    ReadoutSequence,
    PulsedSpectroscopySequence,
    CWSpectroscopySequence,
    CustomSequence,
    TriggerSequence,
)


class SequenceProgram(object):
    """
    SequenceProgram class that holds information about an AWG sequence.
    The class holds a Sequence object, depending on the set type of the sequence.
    the get() method returns the generated string for the seqC program that can 
    be downloaded to the AWG.
    
    """

    def __init__(self, sequence_type=None, **kwargs):
        self._set_type(sequence_type)
        self._sequence = self.sequence_class(**kwargs)

    def get_seqc(self):
        """
        Returns the sequence C code for of the current program as a string.
    
        """
        return self._sequence.get()

    def set_params(self, **settings):
        if "sequence_type" in settings:
            current_params = attr.asdict(self._sequence)
            self.__init__(sequence_type=settings["sequence_type"])
            self._sequence.set(**current_params)
        self._sequence.set(**settings)

    def list_params(self):
        return dict(
            sequence_type=self._sequence_type,
            sequence_parameters=attr.asdict(self._sequence),
        )

    def _set_type(self, type):
        if type is None or type == "None":
            self.sequence_class = Sequence
        elif type == "Simple":
            self.sequence_class = SimpleSequence
        elif type == "Rabi":
            self.sequence_class = RabiSequence
        elif type == "T1":
            self.sequence_class = T1Sequence
        elif type == "T2*":
            self.sequence_class = T2Sequence
        elif type == "Readout":
            self.sequence_class = ReadoutSequence
        elif type == "Pulsed Spectroscopy":
            self.sequence_class = PulsedSpectroscopySequence
        elif type == "CW Spectroscopy":
            self.sequence_class = CWSpectroscopySequence
        elif type == "Custom":
            self.sequence_class = CustomSequence
        elif type == "Trigger":
            self.sequence_class = TriggerSequence
        else:
            raise ValueError("Unknown Sequence Type!")
        self._sequence_type = type

    @property
    def sequence_type(self):
        return self._sequence_type
