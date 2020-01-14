from helpers import Waveform
import zhinst.ziPython as zi
import time


class AWG(object):
    def __init__(self, **kwargs):
        self.awg_module_executed = False
        self.__index = kwargs.get("index", 0)
        self.__daq = None
        self.__awg = None
        self.__queue = []

    def setup(self, daq, device: str):
        if not isinstance(daq, zi.ziDAQServer):
            raise TypeError("not a ziDAQServer!")
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

    def queue_waveform(self, waveform: Waveform):
        if not isinstance(waveform, Waveform):
            raise WaveformUploadError("Parameter waveform has to be a Waveform object!")
        self.__queue.append(waveform)

    def clear_queue(self):
        self.__queue = []

    def upload_waveforms(self):
        if self.awg_module_executed:
            node_data_pairs = []
            for i, waveform in enumerate(self.__queue):
                node_data_pairs.append(
                    (
                        f"/{self.__device}/awgs/{self.index}/waveform/waves/{i}",
                        waveform.data,
                    )
                )
            try:
                self.__daq.set(node_data_pairs)
                self.clear_queue()
            except RuntimeError as e:
                raise e

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
    def queue(self):
        return self.__queue

    @property
    def is_running(self):
        if self.awg_module_executed:
            return bool(self.__awg.getInt("awg/enable"))
        else:
            raise NotConnectedError(
                "AWG not connected, use `awg.setup(daq, device)` to associate AWG to a device."
            )


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
