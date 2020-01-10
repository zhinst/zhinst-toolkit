from .device import Device
from helpers import AWG


class UHFQA(Device):
    """UHFQA class that implements a driver for a UHFQA, inherits from ZiDevice class
    
    Attributes:
    
    Public Methods:
        connect(self, address)

    Typical Usage:
        qa = UHFQA()
        qa.connect("dev2266")
        qa.set_node_value("sigouts/0/on", 1)
        qa.get_node_value("sigouts/0/on")

    """

    def __init__(self):
        self.__awg = AWG()
        self.__awg.set(target="UHFQA", clock_rate=1.8e9)

    def connect(self, device):
        """connect to device, overwrite ZiDevice method
        
        Arguments:
            device {string} -- device string
        """
        super().connect(device, "UHFQA")

    def disconnect(self):
        pass

    def setup_awg(self):
        """setup AWG object, creates awgModule object and 
        executes it

        """
        self.__awg.setup(self._daq, self._device)
        print(f"Started AWG of device {self._device}")

    @property
    def awg(self):
        """use property awgs to access list of AWG objects
        """
        return self.__awg
