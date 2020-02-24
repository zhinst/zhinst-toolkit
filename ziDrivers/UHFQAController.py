import json
import time
import pathlib
import numpy as np

from .controller import Controller
from .connection import ZIDeviceConnection
from .interface import InstrumentConfiguration



class UHFQAController(Controller):
    def __init__(self):
        super().__init__()
        self.__name, self.__index = ("uhfqa0", 0)
        self.type = "uhfqa"

    def setup(self):
        super().setup("connection-uhfqa.json")

    def set_device_connection(self, connection: ZIDeviceConnection):
        filename = "connection-uhfqa.json"
        dir = pathlib.Path(__file__).parent
        instrument_config = dir / "resources" / filename
        try:
            with open(instrument_config) as file:
                data = json.load(file)
                schema = InstrumentConfiguration()
                self._instrument_config = schema.load(data)
            self._connection = connection
        except IOError:
            print(f"File {instrument_config} is not accessible")

    def connect_device(self, address, interface):
        super().connect_device(self.__name, address, interface)


    ####################################################
    # device specific methods

    def set_outputs(self, value):
        if value == "on": value = 1 
        if value == "off": value = 0
        self.set("sigouts/*/on", value)
    
    def write_crottalk_matrix(self, matrix):
        rows, cols = matrix.shape
        assert rows <= 10
        assert cols <= 10
        for r in range(rows):
            for c in range(cols):
                self.set(f"qas/0/crosstalk/rows/{r}/cols/{c}", matrix[r, c])

    def set_rotations(self, rotations):
        assert len(rotations) in range(10)
        for ch, rot in enumerate(rotations):
            self.set_rotation(ch, rot)

    def set_rotation(self, ch, rot):
        assert ch in range(10)
        c = np.exp(1j*np.deg2rad(rot))
        self.set(f"qas/0/rotations/{ch}", c)

    def get_rotations(self):
        return [self.get_rotation(ch) for ch in range(10)]

    def get_rotation(self, ch):
        assert ch in range(10)
        return np.angle(self.get(f"qas/0/rotations/{ch}"), deg=True)

    def set_thresholds(self, thresholds):
        assert len(thresholds) <= 10
        for i, t in enumerate(thresholds):
            self.set(f"qas/0/thresholds/{i}/level", t)

    def set_threshold(self, ch, th):
        assert ch in range(10)
        self.set(f"qas/0/thresholds/{ch}/level", th)

    def get_thresholds(self):
        return [self.get_threshold(ch) for ch in range(10)]

    def get_threshold(self, ch):
        assert ch in range(10)
        return self.get(f"qas/0/thresholds/{ch}/level")

    def get_results(self):
        return [self.get_result(ch) for ch in range(10)]
    
    def get_result(self, ch):
        assert ch in range(10)
        return self.get(f"qas/0/result/data/{ch}/wave")

    # apply device settings depending on sequence settings
    def __apply_sequence_settings(self, **kwargs):
        if "sequence_type" in kwargs.keys():
            t = kwargs["sequence_type"]
            allowed_sequences = [
                "Simple",
                "Readout",
                "CW Spectroscopy",
                "Pulsed Spectroscopy",
                "Custom",
            ]
            if t not in allowed_sequences:
                raise Exception(
                    f"Sequence type {t} must be one of {allowed_sequences}!"
                )
            # apply settings depending on sequence type
            if t == "CW Spectroscopy":
                self.__apply_cw_settings()
            if t == "Pulsed Spectroscopy":
                self.__apply_pulsed_settings()
            if t == "Readout":
                self.__apply_readout_settings()
        # set demodulation weights at readout frequencies
        if "readout_frequencies" in kwargs.keys():
            self.__reset_int_weights()
            self.__set_int_weights(kwargs["readout_frequencies"])
        # apply settings dependent on trigger type
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self.set("/awgs/0/auxtriggers/*/channel", 0)
                self.set("/awgs/0/auxtriggers/*/slope", 1)

    def __apply_cw_settings(self):
        self.set("sigouts/0/enables/0", 1)
        self.set("sigouts/1/enables/1", 1)
        self.set("sigouts/0/amplitudes/0", 1)
        self.set("sigouts/1/amplitudes/1", 1)
        self.set("qas/0/integration/mode", 1)

    def __apply_pulsed_settings(self):
        self.set("sigouts/*/enables/*", 0)
        self.set("sigouts/*/amplitudes/*", 0)
        self.set("awgs/0/outputs/*/mode", 1)
        self.set("qas/0/integration/mode", 1)

    def __apply_readout_settings(self):
        self.set("sigouts/*/enables/*", 0)
        self.set("awgs/0/outputs/*/mode", 0)
        self.set("qas/0/integration/mode", 0)

    def __set_int_weights(self, frequencies):
        int_length = self.get("qas/0/integration/length")
        for i, f in enumerate(frequencies):
            self.__set_int_weights_channel(int_length, i, f)

    def __reset_int_weights(self):
        int_length  = self.get("qas/0/integration/length")
        node = f"/qas/0/integration/weights/"
        for i in range(10):
            self.set(node + f"{i}/real", np.zeros(int_length))
            self.set(node + f"{i}/imag", np.zeros(int_length))

    def __set_int_weights_channel(self, length, ch, freq):
        weights_real = self.__generate_demod_weights(length, freq, 0)
        weights_imag = self.__generate_demod_weights(length, freq, 90)
        node = f"/qas/0/integration/weights/{ch}/"
        self.set(node + "real", weights_real)
        self.set(node + "imag", weights_imag)

    def __generate_demod_weights(self, length, freq, phase):
        assert length <= 4096
        assert freq > 0
        clk_rate = 1.8e9
        x = np.arange(0, length)
        y = np.sin(2 * np.pi * freq * x / clk_rate + np.deg2rad(phase))
        return y


    ##########################################################
    # overwrite old stuff
    
    # overwrite set and get with device name
    def set(self, *args):
        super().set(self.__name, *args)

    def get(self, command, valueonly=True):
        return super().get(self.__name, command, valueonly=valueonly)

    # overwrite parent methods for simplicity
    def awg_run(self):
        super().awg_run(self.__name, self.__index)

    def awg_stop(self):
        super().awg_stop(self.__name, self.__index)

    def awg_compile(self):
        super().awg_compile(self.__name, self.__index)

    def awg_reset_queue(self):
        super().awg_reset_queue(self.__name, self.__index)

    def awg_queue_waveform(self, wave1, wave2):
        super().awg_queue_waveform(self.__name, self.__index, data=(wave1, wave2))

    def awg_replace_waveform(self, wave1, wave2, i=0):
        super().awg_replace_waveform(
            self.__name, self.__index, data=(wave1, wave2), index=i
        )

    def awg_upload_waveforms(self):
        super().awg_upload_waveforms(self.__name, self.__index)

    def awg_compile_and_upload_waveforms(self):
        super().awg_compile_and_upload_waveforms(self.__name, self.__index)

    def awg_set_sequence_params(self, **kwargs):
        self.__apply_sequence_settings(**kwargs)
        super().awg_set_sequence_params(self.__name, self.__index, **kwargs)

    def awg_is_running(self):
        return super().awg_is_running(self.__name, self.__index)

    def awg_list_params(self):
        return super().awg_list_params(self.__name, self.__index)




