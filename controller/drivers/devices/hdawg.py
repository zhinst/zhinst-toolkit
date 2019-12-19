from .device import Device
from .awg import AWG


class HDAWG(Device):
    def __init__(self, device):
        super().__init__(device)

        self.__dio = self._connectivity.dio.device
        # if self.__dio is not None:
        #     super().add_edge(
        #         src=self.name,
        #         dst=self.__dio,
        #         src_label=self.name,
        #         dst_label=self.__dio,
        #         edge_label="DIO",
        #         src_attr={"device": self},
        #     )
        for i in self._connectivity.awgs:
            self._awgs[i.awg] = AWG(i, self)
            # super().add_edge(
            #     src=self.name,
            #     dst=hash(self._awgs[i.awg]),
            #     src_label=self.name,
            #     dst_label=str(i.awg),
            #     edge_label=None,
            #     src_attr={"device": self},
            # )
            # super().stitch_graphs(self._awgs[i.awg].graph)

