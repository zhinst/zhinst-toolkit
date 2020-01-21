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
        # super().__init__(name=self.id, parent=None)
        self.parent = parent
        self.__waveforms = list()
        self.__program = str()

    def set_program(self, program):
        self.__program = program

    def get_program(self):
        return self.__program

    def reset_waveforms(self):
        self.__waveforms = list()

    @property
    def waveforms(self):
        return self.__waveforms

        # for i in range(len(self._channels)):
        #     super().add_edge(
        #         src=hash(self),
        #         dst=str(hash(self)) + str(i),
        #         src_label=self.id,
        #         dst_label=str(i),
        #         edge_label=None,
        #     )

        #     if self._channels[i].wave is not None:
        #         super().add_edge(
        #             src=str(hash(self)) + str(i),
        #             dst=self._channels[i].wave,
        #             src_label=str(i),
        #             dst_label=self._channels[i].wave,
        #             edge_label=None,
        #         )
