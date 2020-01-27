from dataclasses import dataclass


@dataclass
class AWGChannel:
    wave: str
    trig: str
    marker: str


class AWG:
    def __init__(self, configuration, parent):

        self.id = configuration.awg
        self._iq = configuration.config.iq
        self._channels = [
            AWGChannel(i.wave, i.trig, i.marker)
            for i in (configuration.ch0, configuration.ch1)
        ]
        self.parent = parent
        self.__waveforms = list()
        self.__program = str()

    def set_program(self, program):
        self.__program = program

    def reset_waveforms(self):
        self.__waveforms = list()

    @property
    def waveforms(self):
        return self.__waveforms

    @property
    def program(self):
        return None if self.__program == "" else self.__program

