from helpers import Waveform
import time


class AWG(object):
    def __init__(self, **kwargs):
        self.awg_module_executed = False
        self.__index = kwargs.get("index", 0)
        self.__daq = None
        self.__awg = None

    def setup(self, daq, device):
        self.__daq = daq
        self.__device = device
        self.__awg = self.__daq.awgModule()
        self.__awg.set("device", device)
        self.__awg.set("index", self.index)
        self.__awg.execute()
        self.awg_module_executed = True

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

    def upload_program(self, awg_program):
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
                raise CompilationWarning(
                    f"Compiled with warning: {self.__awg.getString('compiler/statusstring')}"
                )
            if self.__awg.getInt("compiler/status") == 0:
                print("Compilation successful!")
        else:
            raise NotConnectedError(
                "AWG not connected, use `awg.setup(daq, device)` to associate AWG to a device."
            )
        self._wait_upload_done()

    def upload_waveform(self, waveform, loop_index=0):
        if not isinstance(waveform, Waveform):
            raise WaveformUploadError("Parameter waveform has to be a Waveform object!")
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
        tik = time.time()
        while self.__daq.getInt(node):
            time.sleep(0.01)
            if time.time() - tik >= timeout:
                raise UploadTimeoutError("Waveform upload timed out!")

    @property
    def index(self):
        return self.__index

    @property
    def is_running(self):
        return bool(self.__awg.getInt("awg/enable"))


class NotConnectedError(Exception):
    pass


class CompilationFailedError(Exception):
    pass


class UploadTimeoutError(Exception):
    pass


class WaveformUploadError(Exception):
    pass


class CompilationWarning(Warning):
    pass

