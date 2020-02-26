class AWG:
    def __init__(self, id, parent):

        self.id = id
        self.parent = parent
        self._waveforms = list()
        self._program = str()

    def set_program(self, program):
        self._program = program

    def reset_waveforms(self):
        self._waveforms = list()

    @property
    def waveforms(self):
        return self._waveforms

    @property
    def program(self):
        return None if self._program == "" else self._program
