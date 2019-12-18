import zhinst
import zhinst.utils

import time
import numpy as np
import textwrap

from attr import attrs, attrib
import attr


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
        pass

    def update(self, settings):
        raise NotImplementedError

    def upload_waveform(self):
        raise NotImplementedError


class SequenceProgramOld(object):
    # convention: all time related parameters in units of seconds!
    def __init__(self, **kwargs):
        self.__set_defaults()  # set default params
        self.set(**kwargs)
        return

    def set(self, **settings):
        for key in settings:
            setattr(self, key, settings[key])
        self.update()
        return

    def get(self):
        return self.__sequence

    def update(self):
        self.__check_attributes()
        if self.sequence_type == "None":
            self.__sequence = "// no sequence defined"
        elif self.sequence_type == "Simple":
            self.__write_sequence_simple_4x2()
        elif self.sequence_type == "Rabi":
            self.__write_sequence_Rabi()
        elif self.sequence_type == "T1":
            self.__write_sequence_T1()
        elif self.sequence_type == "T2*":
            self.__write_sequence_T2()

    def __write_sequence_simple_4x2(self):
        if self.trigger_mode == "None":
            trigger_cmd_1 = "//"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time - self.waveform_buffer)
            dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            trigger_cmd_1 = "setTrigger(1);"
            trigger_cmd_2 = "setTrigger(0);"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time - self.waveform_buffer)
            dead_cycles = self.__time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            trigger_cmd_1 = "waitDigTrigger(1);"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
            dead_cycles = 0 
        waveform_buffer_samples = self.__time_to_cycles(self.waveform_buffer, wait_time=False) // 16 * 16  # multiple of 16
            
        awg_program = textwrap.dedent("""\
            // Simple Sequence - Replace Waveforms

            """)
        for i in range(self.n_HW_loop):
            awg_program += textwrap.dedent("""\
                wave w*N*_1 = randomUniform(_BUFFER_);
                wave w*N*_2 = randomUniform(_BUFFER_);
            """).replace("*N*", "{}".format(i+1))
        awg_program += textwrap.dedent("""\
            
            repeat(_LOOP_){
            
            """)    
        for i in range(self.n_HW_loop):    
            awg_program += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_);
                _TRIGGER-COMMAND-2_
                playWave(w*N*_1, w*N*_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);
                
            """).replace("*N*", "{}".format(i+1)).format(i+1, self.n_HW_loop)
        awg_program += textwrap.dedent("""\
            }
            """)
        
        awg_program = awg_program.replace("_BUFFER_", str(waveform_buffer_samples))
        awg_program = awg_program.replace("_LOOP_", str(self.repetitions))
        awg_program = awg_program.replace("_WAIT-CYCLES-1_", str(wait_cycles))
        awg_program = awg_program.replace("_WAIT-CYCLES-2_", str(dead_cycles))
        awg_program = awg_program.replace("_TRIGGER-COMMAND-1_", trigger_cmd_1)
        awg_program = awg_program.replace("_TRIGGER-COMMAND-2_", trigger_cmd_2)
        awg_program = awg_program.replace("wait(0);", "//")
        if self.trigger_mode == "External Trigger":
            awg_program = awg_program.replace("waitWave();", "//")
        self.__sequence = awg_program
        return
        
    def __write_sequence_Rabi(self):
        gauss_params = self.__get_gauss_params()
        if self.trigger_mode == "None":
            trigger_cmd_1 = "//"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time) - gauss_params[0]/8
            dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            trigger_cmd_1 = "setTrigger(1);"
            trigger_cmd_2 = "setTrigger(0);"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time) - gauss_params[0]/8
            dead_cycles = self.__time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            trigger_cmd_1 = "waitDigTrigger(1);"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
            dead_cycles = 0      
            
        awg_program = textwrap.dedent("""\
            // Rabi Sequence
            
            wave w_1 = gauss(_GAUSS-PARAMS_);
            wave w_2 = drag(_GAUSS-PARAMS_);
            
        """)
        awg_program += textwrap.dedent("""\
        repeat(_LOOP_){

        """)
        for i, amp in enumerate(self.pulse_amplitudes):
            awg_program += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_);
                _TRIGGER-COMMAND-2_
                playWave({}*w_1, {}*w_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);

            """).format(i+1, len(self.pulse_amplitudes), amp, amp)
        awg_program += textwrap.dedent("""\
        }
        """)
        
        awg_program = awg_program.replace("_GAUSS-PARAMS_", ",".join([str(p) for p in gauss_params]))
        awg_program = awg_program.replace("_LOOP_", str(self.repetitions))
        awg_program = awg_program.replace("_WAIT-CYCLES-1_", str(wait_cycles))
        awg_program = awg_program.replace("_WAIT-CYCLES-2_", str(dead_cycles))
        awg_program = awg_program.replace("_TRIGGER-COMMAND-1_", trigger_cmd_1)
        awg_program = awg_program.replace("_TRIGGER-COMMAND-2_", trigger_cmd_2)
        awg_program = awg_program.replace("wait(0);", "//")
        if self.trigger_mode == "Wait Trigger":
            awg_program = awg_program.replace("waitWave();", "//")
        self.__sequence = awg_program    
        return

    def __write_sequence_T1(self):
        gauss_params = self.__get_gauss_params()
        if self.trigger_mode == "None":
            trigger_cmd_1 = "//"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time) - gauss_params[0]/8
            dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            trigger_cmd_1 = "setTrigger(1);"
            trigger_cmd_2 = "setTrigger(0);"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time) - gauss_params[0]/8
            dead_cycles = self.__time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            trigger_cmd_1 = "waitDigTrigger(1);"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
            dead_cycles = 0      
        delay_cycles = np.array([self.__time_to_cycles(t) for t in self.delay_times])    
        
        awg_program = textwrap.dedent("""\
            // T1 Sequence
            
            wave w_1 = {} * gauss(_GAUSS-PARAMS_);
            wave w_2 = {} * drag(_GAUSS-PARAMS_);
            
        """).format(self.pulse_amplitudes[0], self.pulse_amplitudes[0])
        awg_program += textwrap.dedent("""\
        repeat(_LOOP_){

        """)
        for i, t in enumerate(delay_cycles):
            awg_program += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_ - {});
                _TRIGGER-COMMAND-2_
                playWave(w_1, w_2);
                waitWave();
                wait(_WAIT-CYCLES-2_ + {});

            """).format(i+1, len(delay_cycles), t, t)
        awg_program += textwrap.dedent("""\
        }
        """)
        
        awg_program = awg_program.replace("_GAUSS-PARAMS_", ",".join([str(p) for p in gauss_params]))
        awg_program = awg_program.replace("_LOOP_", str(self.repetitions))
        awg_program = awg_program.replace("_WAIT-CYCLES-1_", str(wait_cycles))
        awg_program = awg_program.replace("_WAIT-CYCLES-2_", str(dead_cycles))
        awg_program = awg_program.replace("_TRIGGER-COMMAND-1_", trigger_cmd_1)
        awg_program = awg_program.replace("_TRIGGER-COMMAND-2_", trigger_cmd_2)
        awg_program = awg_program.replace("wait(0);", "//")
        if self.trigger_mode == "Wait Trigger":
            awg_program = awg_program.replace("waitWave();", "//")
        self.__sequence = awg_program    
        return

    def __write_sequence_T2(self):
        gauss_params = self.__get_gauss_params()
        if self.trigger_mode == "None":
            trigger_cmd_1 = "//"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time) - gauss_params[0]/8
            dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            trigger_cmd_1 = "setTrigger(1);"
            trigger_cmd_2 = "setTrigger(0);"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time) - gauss_params[0]/8
            dead_cycles = self.__time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            trigger_cmd_1 = "waitDigTrigger(1);"
            trigger_cmd_2 = "//"
            wait_cycles = self.__time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
            dead_cycles = 0      
        delay_cycles = np.array([self.__time_to_cycles(t) for t in self.delay_times])    
        
        awg_program = textwrap.dedent("""\
            // T2* Sequence
            
            wave w_1 = 0.5 * {} * gauss(_GAUSS-PARAMS_);
            wave w_2 = 0.5 * {} * drag(_GAUSS-PARAMS_);
            
        """).format(self.pulse_amplitudes[0], self.pulse_amplitudes[0])
        awg_program += textwrap.dedent("""\
        repeat(_LOOP_){

        """)
        for i, t in enumerate(delay_cycles):
            awg_program += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_ - {});
                _TRIGGER-COMMAND-2_
                playWave(w_1, w_2);
                wait({});
                playWave(w_1, w_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);

            """).format(i+1, len(delay_cycles), t, t)
        awg_program += textwrap.dedent("""\
        }
        """)
        
        awg_program = awg_program.replace("_GAUSS-PARAMS_", ",".join([str(p) for p in gauss_params]))
        awg_program = awg_program.replace("_LOOP_", str(self.repetitions))
        awg_program = awg_program.replace("_WAIT-CYCLES-1_", str(wait_cycles))
        awg_program = awg_program.replace("_WAIT-CYCLES-2_", str(dead_cycles))
        awg_program = awg_program.replace("_TRIGGER-COMMAND-1_", trigger_cmd_1)
        awg_program = awg_program.replace("_TRIGGER-COMMAND-2_", trigger_cmd_2)
        awg_program = awg_program.replace("wait(0);", "//")
        if self.trigger_mode == "Wait Trigger":
            awg_program = awg_program.replace("waitWave();", "//")
        self.__sequence = awg_program    
        return
    
    def __get_gauss_params(self):
        gauss_length = self.__time_to_cycles(2*self.pulse_truncation*self.pulse_width, wait_time=False) // 16 * 16  # multiple of 16
        gauss_pos = int(gauss_length/2)
        gauss_width = self.__time_to_cycles(self.pulse_width, wait_time=False)
        return [gauss_length, gauss_pos, gauss_width]

    def __time_to_cycles(self, time, wait_time=True):
        if wait_time:
            return int(time * self.clock_rate / 8)
        else:
            return int(time * self.clock_rate)

    def __check_attributes(self):
        assert self.sequence_type in ["None", "Simple", "Rabi", "T1", "T2*"]
        assert self.trigger_mode in ["None", "Send Trigger", "Wait Trigger"]
        assert (self.period - self.dead_time - self.waveform_buffer) > 0
        assert (self.period - self.dead_time - self.latency + self.trigger_delay) > 0
        assert np.max(np.abs(self.pulse_amplitudes)) <= 1.0
        if self.sequence_type == "Simple":
            assert self.waveform_buffer > 0
        if self.sequence_type == "Rabi":
            assert len(self.pulse_amplitudes) >= self.n_HW_loop
        if self.sequence_type in ["T1", "T2*"]:
            assert len(self.delay_times) >= self.n_HW_loop
        return

    def __set_defaults(self):
        self.sequence_type = "None"
        self.clock_rate = 1.8e9
        self.trigger_mode = "None"
        self.repetitions = 1
        self.n_HW_loop = 1
        self.period = 100e-6
        self.dead_time = 5e-6
        self.latency = 160e-9
        self.trigger_delay = 0
        self.waveform_buffer = 1e-6
        self.pulse_amplitudes = np.array([1.0])
        self.delay_times = np.array([0])
        self.pulse_width = 50e-9
        self.pulse_truncation = 4
        self.playWave_latency = 10e-9


#################################################################
# validators here
def is_positive(self, attribute, value):
    if value < 0:
        raise ValueError("Must be positive!")

def amp_smaller_1(self, attribute, value):
    if np.max(np.abs(value)) > 1.0:
        raise ValueError("Amplitude cannot be larger than 1.0!")

#################################################################


@attrs
class SequenceProgram(object):
    sequence_type = attrib(default="None", validator=attr.validators.in_(["None", "Simple", "Rabi", "T1", "T2*"]))


@attrs
class Sequence(object):   
    clock_rate = attrib(default=2.4e9, validator=is_positive)
    period = attrib(default=100e-6, validator=is_positive)
    trigger_mode = attrib(default="None", validator=attr.validators.in_(["None", "Send Trigger", "External Trigger"]))
    repetitions = attrib(default=1, converter=int, validator=is_positive)
    n_HW_loop = attrib(default=1, converter=int, validator=is_positive)
    dead_time = attrib(default=5e-6, validator=is_positive)
    trigger_delay = attrib(default=0)
    latency = attrib(default=160e-9, validator=is_positive)

    def time_to_cycles(self, time, wait_time=True):
        if wait_time:
            return int(time * self.clock_rate / 8)
        else:
            return int(time * self.clock_rate)
        
    def get_gauss_params(self, width, truncation):
        gauss_length = self.__time_to_cycles(2*truncation*width, wait_time=False) // 16 * 16  # multiple of 16
        gauss_pos = int(gauss_length/2)
        gauss_width = self.__time_to_cycles(width, wait_time=False)
        return [gauss_length, gauss_pos, gauss_width]

    def check_attributes(self):
        assert (self.period - self.dead_time - self.latency + self.trigger_delay) > 0

@attrs
class SimpleSequence(Sequence):
    waveform_buffer = attrib(default=1e-6, validator=is_positive)

    def get(self):
        if self.trigger_mode == "None":
            trigger_cmd_1 = "//"
            trigger_cmd_2 = "//"
            wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.waveform_buffer)
            dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            trigger_cmd_1 = "setTrigger(1);"
            trigger_cmd_2 = "setTrigger(0);"
            wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.waveform_buffer)
            dead_cycles = self.time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            trigger_cmd_1 = "waitDigTrigger(1);"
            trigger_cmd_2 = "//"
            wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
            dead_cycles = 0 
        waveform_buffer_samples = self.time_to_cycles(self.waveform_buffer, wait_time=False) // 16 * 16  # multiple of 16
            
        awg_program = textwrap.dedent("""\
            // Simple Sequence - Replace Waveforms

            """)
        for i in range(self.n_HW_loop):
            awg_program += textwrap.dedent("""\
                wave w*N*_1 = randomUniform(_BUFFER_);
                wave w*N*_2 = randomUniform(_BUFFER_);
            """).replace("*N*", "{}".format(i+1))
        awg_program += textwrap.dedent("""\
            
            repeat(_LOOP_){
            
            """)    
        for i in range(self.n_HW_loop):    
            awg_program += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_);
                _TRIGGER-COMMAND-2_
                playWave(w*N*_1, w*N*_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);
                
            """).replace("*N*", "{}".format(i+1)).format(i+1, self.n_HW_loop)
        awg_program += textwrap.dedent("""\
            }
            """)
        awg_program = awg_program.replace("_BUFFER_", str(waveform_buffer_samples))
        awg_program = awg_program.replace("_LOOP_", str(self.repetitions))
        awg_program = awg_program.replace("_WAIT-CYCLES-1_", str(wait_cycles))
        awg_program = awg_program.replace("_WAIT-CYCLES-2_", str(dead_cycles))
        awg_program = awg_program.replace("_TRIGGER-COMMAND-1_", trigger_cmd_1)
        awg_program = awg_program.replace("_TRIGGER-COMMAND-2_", trigger_cmd_2)
        awg_program = awg_program.replace("wait(0);", "//")
        if self.trigger_mode == "External Trigger":
            awg_program = awg_program.replace("waitWave();", "//")
        self.sequence = awg_program
        return self.sequence



class RabiSequence(Sequence):
    rabi_amplitudes = attrib(default=np.linspace(0, 1, 10), validator=amp_smaller_1)

    def get(self):
        self.sequence = "blub"
        return self.sequence

class T1Sequence(Sequence):
    pass

class T2Sequence(Sequence):
    pass

#################################################################
if __name__ == "__main__":
    pass

