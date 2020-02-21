import json
import time

from .controller import Controller



class HDAWGController(Controller):
    def __init__(self):
        super().__init__()
        self.__name = "hdawg0"

    def setup(self):
        super().setup("connection-hdawg.json")

    def connect_device(self, address, interface):
        super().connect_device(self.__name, address, interface)

    # overwrite parent methods for simplicity
    def awg_run(self, awg):
        super().awg_run(self.__name, awg)

    def awg_stop(self, awg):
        super().awg_stop(self.__name, awg)

    def awg_compile(self, awg):
        super().awg_compile(self.__name, awg)

    def awg_reset_queue(self, awg):
        super().awg_reset_queue(self.__name, awg)

    def awg_queue_waveform(self, awg, wave1, wave2):
        super().awg_queue_waveform(self.__name, awg, data=(wave1, wave2))

    def awg_replace_waveform(self, awg, wave1, wave2, i=0):
        super().awg_replace_waveform(
            self.__name, awg, data=(wave1, wave2), index=i
        )

    def awg_upload_waveforms(self, awg):
        super().awg_upload_waveforms(self.__name,awg)

    def awg_compile_and_upload_waveforms(self, awg):
        super().awg_compile_and_upload_waveforms(self.__name, awg)

    def awg_set_sequence_params(self, awg, **kwargs):
        self.__apply_sequence_settings(awg, **kwargs)
        super().awg_set_sequence_params(self.__name, awg, **kwargs)

    def awg_is_running(self, awg):
        return super().awg_is_running(self.__name, awg)

    def awg_list_params(self, awg):
        return super().awg_list_params(self.__name, awg)

    # apply device settings depending on sequence settings
    def __apply_sequence_settings(self, awg, **kwargs):
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
            #
            #
            #
            #