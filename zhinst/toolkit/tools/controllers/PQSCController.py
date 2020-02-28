from .BaseController import BaseController


class PQSCController(BaseController):
    def __init__(self, name, serial, **kwargs):
        super().__init__(name, "pqsc", serial, **kwargs)
