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


    ####################################################
    # device specific methods

    def set_outputs(self, values):
        assert len(values) == 4
        for i, v in enumerate(values):
            self.set_output(i, v)
    
    def set_output(self, awg, value):
        if value == "on": value = 1 
        if value == "off": value = 0
        self.set(f"sigouts/{2 * awg}/on", value)
        self.set(f"sigouts/{2 * awg + 1}/on", value)
    
    def enable_iq_modulation(self, awg):
        if awg == "all":
            [self.enable_iq_modulation(i) for i in range(4)]
        else:
            settings = [
                (f"awgs/{awg}/outputs/0/modulation/mode", 1),    # modulation: sine 11
                (f"awgs/{awg}/outputs/1/modulation/mode", 2),    # modulation: sine 22
                (f"sines/{2 * awg}/oscselect", awg),             # select osc N for awg N
                (f"sines/{2 * awg + 1}/oscselect", awg),         # select osc N for awg N
                (f"sines/{2 * awg + 1}/phaseshift", 90),         # 90 deg phase shift on second channel
            ]
            self.set(settings)

    def set_modulation_frequencies(self, frequencies):
        assert len(frequencies) <= 4
        [self.set_modulation_frequency(i, f) for i, f in enumerate(frequencies)]  

    def set_modulation_frequency(self, awg, freq):
        assert freq > 0
        self.set(f"oscs/{awg}/freq", freq)

    def set_modulation_phases(self, phases):
        assert len(phases) <= 4
        for i, p in enumerate(phases):
            self.set_modulation_phase(i, p)

    def set_modulation_phase(self, awg, p):
        self.set(f"sines/{2 * awg + 1}/phaseshift", p)

    def set_modulation_gains(self, gains):
        assert len(gains) <= 4
        [self.set_modulation_gain(i, g) for i, g in enumerate(gains)]
                  
    def set_modulation_gain(self, awg, g):
        assert len(g) == 2  
        self.set(f"awgs/{awg}/outputs/0/gains/0", g[0])
        self.set(f"awgs/{awg}/outputs/1/gains/1", g[1])

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
        # more here?


    ####################################################
    # overwrite old stuff

    # overwrite set and get with device name
    def set(self, *args):
        super().set(self.__name, *args)

    def get(self, command, valueonly=True):
        return super().get(self.__name, command, valueonly=valueonly)

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