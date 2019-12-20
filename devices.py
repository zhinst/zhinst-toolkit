import zhinst
import zhinst.utils

import time
import numpy as np
import textwrap

from sequences import SequenceProgram


class ZiDevice(object):
    """ZiDevice class that implements basic functionality common to any ZI device
    
    Attributes:
        daq {ziDAQmodule} -- ziPython DAQ module used for the data connection
        device {string} -- device string, e.g. "dev8030"
    
    Public Methods:
        connect(self, address, device_type)
        set_node_value(self, node, value)
        get_node_value(self, node)

    Typical Usage:
        device = ZiDevice()
        device.connect("dev8030", "HDAWG")
        device.set_node_value("sigouts/0/on", 1)
        device.get_node_value("sigouts/0/on")

    """

    #################################################################
    def connect(self, address, device_type, port=8004, api_level=6):
        """open connection to HDAWG device, initialize DAQ object
        
        Arguments:
            object {self} -- self
            address {string} -- device address, e.g. "dev8030" or "dev8030-1" for indexing
            device_type {string} -- required device type, e.g. {"HDAWG", "UHFQA"}
        
        Keyword Arguments:
            port {int} -- default port to discover device (default: {8004})
            api_level {int} -- ziPython API level (default: {6})
        """
        if address == "":
            self.daq = zhinst.utils.autoConnect(default_port=port, api_level=api_level)
            self.device = zhinst.utils.autoDetect(self.daq)
        else:
            address = address.replace("-1", "")
            address = address.replace("-2", "")
            (self.daq, self.device, _) = zhinst.utils.create_api_session(
                address,
                api_level,
                required_devtype=device_type,
                required_err_msg="This driver requires a {}!".format(device_type),
            )
        return

    #################################################################
    #
    # setting/getting of node values
    #################################################################
    def set_node_value(self, set_command, value):
        """sets the node value of the given node
        
        Arguments:
            set_command {string} -- node path, device does not need to be specified
            value {} -- value to be set, various datatypes
        
        Returns:
            vaious datatypes -- value actually set on device
        """
        node = (
            "/{}/".format(self.device)
            + set_command  # bring node path to format "/dev8030/.../.."
        )
        dtype = self.__get_node_datatype(node)
        # set parameter
        self.__set_parameter(node, dtype(value))
        return self.get_node_value(node)

    #################################################################
    def __set_parameter(self, node, value):
        """set value for given node depending on datatype
        
        Arguments:
            node {string} -- node path, device needs to be be specified
            value {various} -- actual value to be set
        """
        if isinstance(value, float):
            self.daq.asyncSetDouble(node, value)
        elif isinstance(value, int):
            self.daq.asyncSetInt(node, value)
        elif isinstance(value, str):
            self.daq.asyncSetString(node, value)
        elif isinstance(value, complex):
            self.daq.setComplex(node, value)
        return

    #################################################################
    def get_node_value(self, node):
        """method to get value of node from device
        
        Arguments:
            node {string} -- node path, device may be specified
        
        Returns:
            various -- value on device
        """
        if self.device not in node:
            node = "/{}/".format(self.device) + node
        dtype = self.__get_node_datatype(node)
        # read data from ZI
        d = self.daq.get(node, flat=True)
        assert len(d) > 0
        # extract and return data
        data = next(iter(d.values()))
        # all others
        if isinstance(data, dict) and "value" in data:
            data = data["value"]
        value = dtype(data[0])
        return value

    #################################################################
    def __get_node_datatype(self, node):
        """return datatype of node
        
        Arguments:
            node {string} -- node path, device must be specified
        
        Returns:
            dtype -- datatype of node, in {str, int, float, complex}
        """
        # used cached value, if available
        if not hasattr(self, "_node_datatypes"):
            self.__node_datatypes = dict()
        if node in self.__node_datatypes:
            return self.__node_datatypes[node]
        # find datatype from returned data
        d = self.daq.get(node, flat=True)
        assert len(d) > 0
        data = next(iter(d.values()))
        # if returning dict, strip timing information (API level 6)
        if isinstance(data, list):
            data = data[0]
        if isinstance(data, dict) and "value" in data:
            data = data["value"]
        if isinstance(data, dict) and "vector" in data:
            data = data["vector"]
        # get first item, if python list assume string
        if isinstance(data, list):
            dtype = str
        # not string, should be np array, check dtype
        elif data.dtype in (int, np.int_, np.int64, np.int32, np.int16):
            dtype = int
        elif data.dtype in (float, np.float_, np.float64, np.float32):
            dtype = float
        elif data.dtype in (complex, np.complex_, np.complex64, np.complex128):
            dtype = complex
        # else: ERROR
        # keep track of datatype for future use
        self.__node_datatypes[node] = dtype
        return dtype


class HDAWG(ZiDevice):
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


class UHFQA(ZiDevice):
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

    def connect(self, device):
        """connect to device, overwrite ZiDevice method
        
        Arguments:
            device {string} -- device string
        """
        super().connect(device, "UHFQA")


class AWG(object):
    def __init__(self):
        self.in_use = False
        self.__sequence = SequenceProgram()
        self.awg = None  # daq.awgModule()
        self.waveforms = []

    def set(self, **settings):
        self.__sequence.set(**settings)

    def update(self):
        if self.__sequence.sequence_type == "Simple":
            if len(self.waveforms) == 0:
                raise Exception("No Waveforms defined!")
            self.__sequence.set(
                buffer_lengths=[w.buffer_length for w in self.waveforms]
            )
        print("Uploaded sequence program to device!") # self.upload_program(self.__sequence.get())

    def add_waveform(self, wave1, wave2):
        if self.__sequence.sequence_type == "Simple":
            w = Waveform(wave1, wave2)
            self.waveforms.append(w)
            print("added waveform of length 2 x {}".format(w.buffer_length))
        else:
            print("AWG Sequence type must be 'Simple' to upload waveforms!")

    def upload_waveforms(self):
        self.update()
        for w in self.waveforms:
            self.upload_waveform(w)
        print("Finished uploading {} waveforms!".format(len(self.waveforms)))
        self.waveforms = []

    def upload_waveform(self, waveform):
        print("     ... uploaded waveform of length 2 x {}".format(waveform.buffer_length))

    def print_sequence(self):
        print(self.__sequence.get())


class Waveform(object):
    def __init__(self, wave1, wave2, granularity=16, align_start=True):
        self.granularity = granularity
        self.align_start = align_start
        self.buffer_length = self.round_up(max(len(wave1), len(wave2), 16))
        self.data = self.interleave_waveforms(wave1, wave2)

    def interleave_waveforms(self, x1, x2):
        if len(x1) == 0:
            x1 = np.zeros(1)
        if len(x2) == 0:
            x2 = np.zeros(1)

        n = max(len(x1), len(x2))
        n = min(n, self.buffer_length)
        m1, m2 = np.max(np.abs(x1)), np.max(np.abs(x2))
        data = np.zeros((2, self.buffer_length))

        if self.align_start:
            if len(x1) > n:
                data[0, :n] = x1[:n] / m1 if m1 >= 1 else x1[:n]
            else:
                data[0, : len(x1)] = x1 / m1 if m1 >= 1 else x1
            if len(x2) > n:
                data[1, :n] = x2[:n] / m2 if m2 >= 1 else x2[:n]
            else:
                data[1, : len(x2)] = x2 / m2 if m2 >= 1 else x2
        else:
            if len(x1) > n:
                data[0, :n] = x1[len(x1) - n :] / m1 if m1 >= 1 else x1[len(x1) - n :]
            else:
                data[0, (self.buffer_length - len(x1)) :] = x1 / m1 if m1 >= 1 else x1

            if len(x2) > n:
                data[1, :n] = x2[len(x2) - n :] / m2 if m2 >= 1 else x2[len(x2) - n :]
            else:
                data[1, (self.buffer_length - len(x2)) :] = x2 / m2 if m2 >= 1 else x2

        interleaved_data = (data.reshape((-2,), order="F") * (2 ** 15 - 1)).astype(
            "int16"
        )
        return interleaved_data

    def round_up(self, n):
        m, rest = divmod(n, self.granularity)
        if not rest:
            return n
        else:
            return (m + 1) * self.granularity


#################################################################
if __name__ == "__main__":
    pass

