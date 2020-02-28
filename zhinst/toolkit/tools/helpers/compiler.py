from .sequenceProgram import SequenceProgram


class Compiler:
    def __init__(self, **kwargs):
        self._sequencers = dict()
        self._device = None

    def add_device(self, device):
        self._device = device
        for i in device.awgs.keys():
            self._sequencers[self._to_key(i)] = SequenceProgram()
            self._sequencers[self._to_key(i)].set(target=device.device_type)

    def set_parameter(self, awg, **kwargs):
        self._sequencers[self._to_key(awg)].set(**kwargs)

    def list_params(self, awg):
        return self._sequencers[self._to_key(awg)].list_params()

    def get_program(self, awg):
        return self._sequencers[self._to_key(awg)].get()

    def sequence_type(self, awg):
        return self._sequencers[self._to_key(awg)].sequence_type

    def _to_key(self, awg):
        return str(self._device.name + "-" + str(awg))
