from waveform import Waveform
from sequences import SequenceProgram


class AWG(object):
    def __init__(self):
        self.in_use = False
        self.__sequence = SequenceProgram()
        self.awg = None  # daq.awgModule()
        self.waveforms = []

    def set(self, **settings):
        self.__sequence.set(**settings)

    def update(self):
        if self.__sequence.sequence_type == "Simple":
            if len(self.waveforms) == 0:
                raise Exception("No Waveforms defined!")
            self.__sequence.set(
                buffer_lengths=[w.buffer_length for w in self.waveforms]
            )
        print(
            "Uploaded sequence program to device!"
        )  # self.upload_program(self.__sequence.get())

    def add_waveform(self, wave1, wave2):
        if self.__sequence.sequence_type == "Simple":
            w = Waveform(wave1, wave2)
            self.waveforms.append(w)
            print("added waveform of length 2 x {}".format(w.buffer_length))
        else:
            print("AWG Sequence type must be 'Simple' to upload waveforms!")

    def upload_waveforms(self):
        self.update()
        for i, w in enumerate(self.waveforms):
            self.upload_waveform(w, i)
        print("Finished uploading {} waveforms!".format(len(self.waveforms)))
        self.waveforms = []

    def run(self):
        pass

    def _init_awg(self):
        pass

    def _upload_program(self):
        pass

    def upload_waveform(self, waveform, index=0):
        print(
            "     ... uploaded waveform of length 2 x {}".format(waveform.buffer_length)
        )

    def print_sequence(self):
        print(self.__sequence.get())

    def sequence_params(self):
        return self.__sequence.list_params()
