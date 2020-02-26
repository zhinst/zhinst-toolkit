from .sequenceProgram import SequenceProgram


class Compiler:
    def __init__(self, **kwargs):
        self._sequencers = dict()
        self._devices = list()

    def add_device(self, device):
        self._devices.append(device)
        for i in device.awgs.keys():
            self._sequencers[self._to_key(device.name, i)] = SequenceProgram()
            self._sequencers[self._to_key(device.name, i)].set(
                target=device.device_type
            )

    def set_parameter(self, dev, awg, **kwargs):
        self._sequencers[self._to_key(dev, awg)].set(**kwargs)

    def list_params(self, dev, awg):
        return self._sequencers[self._to_key(dev, awg)].list_params()

    def get_program(self, dev, awg):
        return self._sequencers[self._to_key(dev, awg)].get()

    def sequence_type(self, dev, awg):
        return self._sequencers[self._to_key(dev, awg)].sequence_type

    def _to_key(self, dev, awg):
        return str(dev + "-" + str(awg))
