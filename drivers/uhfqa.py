from .device import Device
from .awg import AWG


class UHFQA(Device):
    def __init__(self, **kwargs):
        self.__awgs = {}
        super().__init__(**kwargs, main_component="true")

        for key, value in kwargs["properties"].items():
            if key.startswith("awg"):
                super().add_node(name=super().name + key)
                self.__awgs[key] = AWG(
                    name=super().name + key, properties=value, label=key
                )
                super().update_labels(self.__awgs[key].labels)
                super().compose(self.__awgs[key].graph)
            elif key.startswith("dio"):
                if value is not None:
                    super().add_node(name=kwargs["name"] + key, label=key)

    # def connect(self, device):
    #     super().connect(device, "UHFQA")

    # def disconnect(self):
    #     pass

    # def setup_awg(self):
    #     self.__awg.setup(self._daq, self._device)
    #     print(f"Started AWG of device {self._device}")

    @property
    def awg(self):
        return self.__awgs
