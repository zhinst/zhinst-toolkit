from helpers import SequenceProgram


class Compiler:
    def __init__(self, device, **kwargs):
        self.__sequencers = dict()
        self.__device = device
        for i in self.__device.connectivity.awgs:
            self.__sequencers[i.awg] = SequenceProgram()
            self.__sequencers[i.awg].set(target=self.__device.config.device_type)
        # maybe add channel grouping or something

    def set_parameter(self, awg, **kwargs):
        self.__sequencers[awg].set(**kwargs)

    def list_params(self, awg):
        return self.__sequencers[awg].list_params()

    def get_program(self, awg):
        return self.__sequencers[awg].get()

    def sequence_type(self, awg):
        return self.__sequencers[awg].sequence_type

