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
)


class SequenceProgram(object):
    """SequenceProgram class that holds information about an AWG sequence.
    The class holds a Sequence object, depending on the set type of the sequence.
    the get() method returns the generated string for the seqC program that can 
    be downloaded to the AWG.
    
    Typical Usage:

        s = SequenceProgram()
        s.set(sequence_type="T1")
        s.set(delay_times=np.linspace(0, 10e-6, 11), period=20e-6, trigger_mode="Send Trigger")
        s.set(period=-1)
            > ValueError("Period must be positive!")
        
        s.list_params()
            > {'sequence_type': 'T1',
            >  'sequence_parameters': {'clock_rate': 2400000000.0,
            >  'period': 2e-05,
            >   ...

        print(s.get())
            > // Zurich Instruments sequencer program
            > // sequence type:              T1
            > // automatically generated:    20/12/2019 @10:47
            >
            > wave w_1 = 1 * gauss(720, 360, 120);
            > wave w_2 = 1 * drag(720, 360, 120);
            > ...
    
    """

    def __init__(self, sequence_type=None, **kwargs):
        self._set_type(sequence_type)
        self._sequence = self.sequence_class(**kwargs)

    def get(self):
        return self._sequence.get()

    def set(self, **settings):
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
        else:
            raise ValueError("Unknown Sequence Type!")
        self._sequence_type = type

    @property
    def sequence_type(self):
        return self._sequence_type
