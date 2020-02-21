import json
import time

from .controller import Controller



class UHFQAController(Controller):
    def __init__(self):
        super().__init__()
        self.__name, self.__index = ("uhfqa0", 0)

    def setup(self):
        super().setup("connection-uhfqa.json")

    def connect_device(self, address, interface):
        super().connect_device(self.__name, address, interface)



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
                self.set(self.__name, "sigouts/0/enables/0", 1)
                self.set(self.__name, "sigouts/1/enables/1", 1)
                self.set(self.__name, "sigouts/0/amplitudes/0", 1)
                self.set(self.__name, "sigouts/1/amplitudes/1", 1)
                self.set(self.__name, "qas/0/integration/mode", 1)
            if t == "Pulsed Spectroscopy":
                self.set(self.__name, "sigouts/*/enables/*", 0)
                self.set(self.__name, "sigouts/*/amplitudes/*", 0)
                self.set(self.__name, "awgs/0/outputs/*/mode", 1)
                self.set(self.__name, "qas/0/integration/mode", 1)
            if t == "Readout":
                self.set(self.__name, "sigouts/*/enables/*", 0)
                self.set(self.__name, "awgs/0/outputs/*/mode", 0)
                self.set(self.__name, "qas/0/integration/mode", 0)
        # apply settings dependent on trigger type
        if "trigger_mode" in kwargs.keys():
            if kwargs["trigger_mode"] == "External Trigger":
                self.set(self.__name, "/awgs/0/auxtriggers/*/channel", 0)
                self.set(self.__name, "/awgs/0/auxtriggers/*/slope", 1)


    ##########################################################
    # overwrite old stuff
    
    # overwrite set and get with device name
    def set(self, *args):
        super().set(self.__name, *args)

    def get(self, command, valueonly=True):
        super().get(self.__name, command, valueonly=valueonly)

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
