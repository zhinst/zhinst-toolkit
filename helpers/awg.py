from helpers import Waveform
from helpers import SequenceProgram
import time


class NotConnectedError(Exception):
    pass


class CompilationFailedError(Exception):
    pass


class UploadTimeoutError(Exception):
    pass


class AWG(object):
    def __init__(self, **kwargs):
        self.in_use = False
        self.awg_module_executed = False
        self.__waveforms = []
        self.__index = kwargs.get("index", 0)
        self.__sequence = SequenceProgram()
        self.__daq = None
        self.__awg = None

    def set(self, **settings):
        self.__sequence.set(**settings)

    def update(self):
        if self.__sequence.sequence_type == "Simple":
            if len(self.__waveforms) == 0:
                raise Exception("No Waveforms defined!")
            self.__sequence.set(
                buffer_lengths=[w.buffer_length for w in self.__waveforms]
            )
        self._upload_program(self.__sequence.get())
        print("Uploaded sequence program to device!")

    def add_waveform(self, wave1, wave2):
        if self.__sequence.sequence_type == "Simple":
            w = Waveform(wave1, wave2)
            self.__waveforms.append(w)
        else:
            print("AWG Sequence type must be 'Simple' to upload waveforms!")

    def upload_waveforms(self):
        self.update()
        for i, w in enumerate(self.__waveforms):
            self._upload_waveform(w, i)
        print(f"Finished uploading {len(self.__waveforms)} waveforms!")
        self.__waveforms = []

    def run(self):
        if self.awg_module_executed:
            if not self.__awg.getInt("awg/enable"):
                self.__awg.set("awg/enable", 1)
        else:
            raise NotConnectedError(
                "AWG not connected, use `awg.setup(daq, device)` to associate AWG to a device."
            )

    def stop(self):
        if self.awg_module_executed:
            if self.__awg.getInt("awg/enable"):
                self.__awg.set("awg/enable", 0)
        else:
            raise NotConnectedError(
                "AWG not connected, use `awg.setup(daq, device)` to associate AWG to a device."
            )

    def setup(self, daq, device):
        self.__daq = daq
        self.__device = device
        self.__awg = self.__daq.awgModule()
        self.__awg.set("device", device)
        self.__awg.set("index", self.index)
        self.__awg.execute()
        self.awg_module_executed = True
        self.in_use = True

    def _upload_program(self, awg_program):
        if self.awg_module_executed:
            self.__awg.set("compiler/sourcestring", awg_program)
            while self.__awg.getInt("compiler/status") == -1:
                time.sleep(0.1)
            print(f"Compiler Status: {self.__awg.getInt('compiler/status')}")
            if self.__awg.getInt("compiler/status") == 1:
                raise CompilationFailedError(
                    "Upload failed:\n" + self.__awg.getString("compiler/statusstring")
                )
            if self.__awg.getInt("compiler/status") == 2:
                # warning
                pass
            if self.__awg.getInt("compiler/status") == 0:
                # successful
                pass
        else:
            raise NotConnectedError(
                "AWG not connected, use `awg.setup(daq, device)` to associate AWG to a device."
            )
        self._wait_upload_done()

    def _upload_waveform(self, waveform, loop_index=0):
        if self.awg_module_executed:
            node = f"/{self.__device}/awgs/{self.index}/waveform/waves/{loop_index}"
            self.__daq.setVector(node, waveform.data)
        else:
            raise NotConnectedError(
                "AWG not connected, use `awg.setup(daq, device)` to associate AWG to a device."
            )

    def _wait_upload_done(self, timeout=10):
        time.sleep(0.2)
        node = f"/{self.__device}/awgs/{self.index}/sequencer/status"
        print(f"Status: {self.__daq.getInt(node)} ")
        tik = time.time()
        while self.__daq.getInt(node):
            print(f"Status: {self.__daq.getInt(node)}")
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise UploadTimeoutError()
        print(f"Status: {self.__daq.getInt(node)}")

    def get_sequence(self):
        return self.__sequence.get()

    @property
    def sequence_params(self):
        return self.__sequence.list_params()

    @property
    def index(self):
        return self.__index

    @property
    def waveforms(self):
        return self.__waveforms

    @property
    def is_running(self):
        return bool(self.__awg.getInt("awg/enable"))

