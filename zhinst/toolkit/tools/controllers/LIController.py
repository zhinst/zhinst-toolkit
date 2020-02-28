from .BaseController import BaseController


class LIController(BaseController):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "uhfli", serial, **kwargs)
