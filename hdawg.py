from device import Device


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

    def connect(self, device):
        """connect to device, overwrite ZiDevice method
        
        Arguments:
            device {string} -- device string
        """
        super().connect(device, "HDAWG")
