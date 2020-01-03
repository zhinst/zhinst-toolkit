from .device import Device
from .awg import AWG


class HDAWG(Device):
    """
    Typical Usage:
        >>> hd = HDAWG()
        >>> hd.connect("dev8030")
        >>> hd.set_node_value("sigouts/0/on", 1)
        >>> hd.get_node_value("sigouts/0/on") --> 1
        >>> hd.setup_awg(0)
        >>> hd.awgs[0].set(sequence_type="Simple")
        >>> hd.awgs[0].add_waveform(np.linspace(-1, 1, 100), np.lispace(1, -1, 100))
        >>> hd.upload_waveforms()
        >>> hd.awgs[0].run() 
    """

    def __init__(self, hdawg8=True, **kwargs):
        self.__n_channels = 8 if hdawg8 else 4
        self.__awgs = []
        for i in range(int(self.__n_channels / 2)):
            self.__awgs.append(AWG(index=i))
        pass

    def connect(self, device):
        """connect to device, overwrite Device method
        
        Arguments:
            device {string} -- device ID, e.g. "dev8030"
        """
        super().connect(device, "HDAWG")

    def disconnect(self):
        pass

    def setup_awg(self, i):
        """setup AWG object with index i, creates awgModule object and 
        executes it
        
        Arguments:
            i {int} -- index of AWG
        """
        self.__awgs[i].setup(self._daq, self._device)
        print("Started AWG {} of device {}".format(i, self._device))

    @property
    def awgs(self):
        """use property awgs to access list of AWG objects
        """
        return self.__awgs

