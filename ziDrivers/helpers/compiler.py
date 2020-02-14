from .sequenceProgram import SequenceProgram


class Compiler:
    def __init__(self, **kwargs):
        self.__sequencers = dict()
        self.__devices = list()

    def add_device(self, device):
        self.__devices.append(device)
        for i in device.connectivity.awgs:
            self.__sequencers[self.__to_key(device.name, i.awg)] = SequenceProgram()
            self.__sequencers[self.__to_key(device.name, i.awg)].set(
                target=device.config.device_type
            )

    def set_parameter(self, dev, awg, **kwargs):
        self.__sequencers[self.__to_key(dev, awg)].set(**kwargs)

    def list_params(self, dev, awg):
        return self.__sequencers[self.__to_key(dev, awg)].list_params()

    def get_program(self, dev, awg):
        return self.__sequencers[self.__to_key(dev, awg)].get()

    def sequence_type(self, dev, awg):
        return self.__sequencers[self.__to_key(dev, awg)].sequence_type

    def __to_key(self, dev, awg):
        return str(dev + "-" + str(awg))

