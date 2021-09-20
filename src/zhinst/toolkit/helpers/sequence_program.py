# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import attr
from .utils import SequenceType
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
    """SequenceProgram class that holds information about an AWG sequence.

    The class holds a Sequence object, depending on the set type of the sequence.
    the get() method returns the generated string for the seqC program that can
    be downloaded to the AWG.

    Keyword Arguments:
        sequence_type (str): type of the sequence program, one of {'Simple',
        'Rabi', 'T1', 'T2', 'Readout', 'Pulsed Spectroscopy', 'CW Spectroscopy',
        'Custom', 'Trigger'}

    Properties:
        sequence_type (str): The type of the current sequence program.

    """

    def __init__(self, sequence_type: SequenceType = SequenceType.NONE, **kwargs):
        self._set_type(sequence_type)
        self._sequence = self.sequence_class(**kwargs)

    def get_seqc(self):
        """Get the sequence program.

        Returns:
            The sequence C code for of the current program as a string.

        """
        return self._sequence.get()[0]

    def get_seqc_ct(self):
        """Get the sequence program.

        Returns:
            The sequence C code for of the current program as a string.

        """
        return self._sequence.get()

    def set_params(self, **settings):
        """Sets the sequence parameters of the sequence program."""
        if "sequence_type" in settings:
            current_params = attr.asdict(self._sequence)
            for key in settings.keys():
                current_params[key] = settings[key]
            self.__init__(sequence_type=settings["sequence_type"])
            self._sequence.set(**current_params)
        else:
            self._sequence.set(**settings)

    def list_params(self):
        """List all the current sequence parameters.

        Returns:
            A dictionary with all the seuqence parameters.

        """
        return dict(
            sequence_type=self._sequence_type,
            sequence_parameters=attr.asdict(self._sequence),
        )

    def _set_type(self, t: SequenceType):
        if t == "None":
            t = None
        elif t in ["Ramsey", "T2"]:
            t = "T2*"
        t = SequenceType(t)
        sequence_classes = {
            SequenceType.NONE: Sequence,
            SequenceType.SIMPLE: SimpleSequence,
            SequenceType.RABI: RabiSequence,
            SequenceType.T1: T1Sequence,
            SequenceType.T2: T2Sequence,
            SequenceType.READOUT: ReadoutSequence,
            SequenceType.PULSED_SPEC: PulsedSpectroscopySequence,
            SequenceType.CW_SPEC: CWSpectroscopySequence,
            SequenceType.CUSTOM: CustomSequence,
            SequenceType.TRIGGER: TriggerSequence,
        }
        self.sequence_class = sequence_classes[t]
        self._sequence_type = t

    @property
    def sequence_type(self):
        return self._sequence_type
