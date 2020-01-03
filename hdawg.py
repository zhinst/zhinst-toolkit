from device import Device
from awg import AWG


class HDAWG(Device):
    """HDAWG class that implements a driver for a HDAWG, inherits from ZiDevice class
    
    Attributes:
    
    Public Methods:
        connect(self, address)

    Typical Usage:
        hd = HDAWG()
        hd.connect("dev8030")
        hd.set_node_value("sigouts/0/on", 1)
        hd.get_node_value("sigouts/0/on")

    """

    def __init__(self, hdawg8=True, **kwargs):
        self.__n_channels = 8 if hdawg8 else 4
        self.__awgs = []
        for i in range(int(self.__n_channels / 2)):
            self.__awgs.append(AWG(index=i))
        pass

    def connect(self, device):
        """connect to device, overwrite ZiDevice method
        
        Arguments:
            device {string} -- device string
        """
        super().connect(device, "HDAWG")

    def disconnect(self):
        pass

    def setup_awg(self, i):
        self.__awgs[i].setup(self._daq, self._device)
        print("Started AWG {} of device {}".format(i, self._device))

    @property
    def awgs(self):
        return self.__awgs

