from waveform import Waveform
from sequenceProgram import SequenceProgram
import time


class AWG(object):
    def __init__(self):
        self.in_use = False
        self.waveforms = []
        self.awg_module_executed = False
        self.__sequence = SequenceProgram()
        self.__daq = None
        self.__awg = None

    def set(self, **settings):
        self.__sequence.set(**settings)

    def update(self):
        if self.__sequence.sequence_type == "Simple":
            if len(self.waveforms) == 0:
                raise Exception("No Waveforms defined!")
            self.__sequence.set(
                buffer_lengths=[w.buffer_length for w in self.waveforms]
            )
        self._upload_program(self.__sequence.get())
        print("Uploaded sequence program to device!")

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

    def setup(self, daq, device, index):
        self.__daq = daq
        self.device = device
        self.awg_index = index
        self.__awg = self.__daq.awgModule()
        self.__awg.set("device", device)
        self.__awg.set("index", index)
        self.__awg.execute()
        self.awg_module_executed = True

    def _upload_program(self, awg_program):
        if self.awg_module_executed:
            self.__awg.set("compiler/sourcestring", awg_program)
            time.sleep(1)
            print("Compiler Status: {}".format(self.__awg.getInt("compiler/status")))
            if self.__awg.getInt("compiler/status") == 1:
                raise Exception(
                    "Upload failed:\n" + self.__awg.getString("compiler/statusstring")
                )
            if self.__awg.getInt("compiler/status") == 2:
                # warning
                pass
            if self.__awg.getInt("compiler/status") == 0:
                # successful
                pass

    def upload_waveform(self, waveform, loop_index=0):
        if self.awg_module_executed:
            node = "/{}/awgs/{}/waveform/waves/{}".format(
                self.device, self.awg_index, loop_index
            )
            print("node: {}".format(node))
            print("data: {}".format(waveform.data))
            self.__daq.setVector(node, waveform.data)
            print(
                "     ... uploaded waveform of length 2 x {}".format(
                    waveform.buffer_length
                )
            )

    def get_sequence(self):
        return self.__sequence.get()

    @property
    def sequence_params(self):
        return self.__sequence.list_params()
