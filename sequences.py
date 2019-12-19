import numpy as np
import textwrap
from attr import attrs, attrib
import attr
from seqCommands import SeqCommand


#################################################################
# validators here
def is_positive(self, attribute, value):
    if value < 0:
        raise ValueError("Must be positive!")

def amp_smaller_1(self, attribute, value):
    if np.max(np.abs(value)) > 1.0:
        raise ValueError("Amplitude cannot be larger than 1.0!")

#################################################################


class SequenceProgram(object):
    
    def __init__(self, sequence_type, **kwargs):
        self.__set_type(sequence_type)
        self.sequence = self.sequence_class(**kwargs)        
    
    def get(self):
        return self.sequence.get()

    def set(self, **settings):
        if "sequence_type" in settings:
            current_params = attr.asdict(self.sequence)
            self.__init__(settings["sequence_type"])
            self.sequence.set(**current_params) 
        self.sequence.set(**settings)

    def __set_type(self, type):
        if type == "None":
            self.sequence_class = Sequence
        elif type == "Simple":
            self.sequence_class = SimpleSequence
        elif type == "Rabi":
            self.sequence_class = RabiSequence
        elif type == "T1":
            self.sequence_class = T1Sequence
        elif type == "T2*":
            self.sequence_class = T2Sequence
        else:
            raise ValueError("Unknown Sequence Type!")
        self.sequence_type = type


@attrs
class Sequence(object):   
    clock_rate      = attrib(default=2.4e9, validator=is_positive)
    period          = attrib(default=100e-6, validator=is_positive)
    trigger_mode    = attrib(default="None", validator=attr.validators.in_(["None", "Send Trigger", "External Trigger"]))
    repetitions     = attrib(default=1, converter=int, validator=is_positive)
    n_HW_loop       = attrib(default=1, converter=int, validator=is_positive)
    dead_time       = attrib(default=5e-6, validator=is_positive)
    trigger_delay   = attrib(default=0)
    latency         = attrib(default=160e-9, validator=is_positive)
    # params to replace placeholders in sequence
    trigger_cmd_1 = attrib(default="//")
    trigger_cmd_2 = attrib(default="//")
    wait_cycles = attrib(default=0)
    dead_cycles = attrib(default=0)

    def set(self, **settings):
        for key in settings:
            if hasattr(self, key):
                setattr(self, key, settings[key])
        self.update_params()
        self.check_attributes()
    
    def get(self):
        self.update_params()
        self.check_attributes()
        self.write_sequence()
        self.replace_params()
        return self.sequence

    # main method to define sequence, will be overwritten
    def write_sequence(self):
        self.sequence = "// base Sequence"

    def update_params(self):
        if self.trigger_mode == "None":
            self.trigger_cmd_1 = "//"
            self.trigger_cmd_2 = "//"
            self.dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            self.trigger_cmd_1 = "setTrigger(1);"
            self.trigger_cmd_2 = "setTrigger(0);"
            self.dead_cycles = self.time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.trigger_cmd_1 = "waitDigTrigger(1);"
            self.trigger_cmd_2 = "//"
            self.dead_cycles = 0      
    
    def replace_params(self):
        self.sequence = self.sequence.replace("_LOOP_", str(self.repetitions))
        self.sequence = self.sequence.replace("_WAIT-CYCLES-1_", str(int(self.wait_cycles)))
        self.sequence = self.sequence.replace("_WAIT-CYCLES-2_", str(self.dead_cycles))
        self.sequence = self.sequence.replace("_TRIGGER-COMMAND-1_", self.trigger_cmd_1)
        self.sequence = self.sequence.replace("_TRIGGER-COMMAND-2_", self.trigger_cmd_2)
        self.sequence = self.sequence.replace("wait(0);", "//")
        if self.trigger_mode == "External Trigger":
            self.sequence = self.sequence.replace("waitWave();", "//")

    def time_to_cycles(self, time, wait_time=True):
        if wait_time:
            return int(time * self.clock_rate / 8)
        else:
            return int(time * self.clock_rate)
        
    def get_gauss_params(self, width, truncation):
        gauss_length = self.time_to_cycles(2*truncation*width, wait_time=False) // 16 * 16  # multiple of 16
        gauss_pos = int(gauss_length/2)
        gauss_width = self.time_to_cycles(width, wait_time=False)
        self.gauss_params = [gauss_length, gauss_pos, gauss_width]

    def check_attributes(self):
        if (self.period - self.dead_time - self.latency + self.trigger_delay) < 0: 
            raise ValueError("Wait time cannot be negative!")

    def __setattr__(self, name, value) -> None:
        """Call the validator when we set the field (by default it only runs on __init__)"""
        for attribute in [a for a in getattr(self.__class__, '__attrs_attrs__', []) if a.name == name]:
            if attribute.type is not None:
                if isinstance(value, attribute.type) is False:
                    raise TypeError('{}.{} cannot set {} because it is not a {}'.format(
                        self.__class__.__name__, attribute.name, value, attribute.type.__name__))
            if attribute.validator is not None:
                attribute.validator(self, attribute, value)
        super().__setattr__(name, value)

@attrs
class SimpleSequence(Sequence):
    waveform_buffer = attrib(default=1e-6, validator=is_positive)
    waveform_buffer_samples = attrib(default=16)

    def write_sequence(self):            
        self.sequence = textwrap.dedent("""\
            // Simple Sequence - Replace Waveforms

            """)
        for i in range(self.n_HW_loop):
            self.sequence += textwrap.dedent("""\
                wave w*N*_1 = randomUniform(_BUFFER_);
                wave w*N*_2 = randomUniform(_BUFFER_);
            """).replace("*N*", "{}".format(i+1))
        self.sequence += textwrap.dedent("""\
            
            repeat(_LOOP_){
            
            """)    
        for i in range(self.n_HW_loop):    
            self.sequence += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_);
                _TRIGGER-COMMAND-2_
                playWave(w*N*_1, w*N*_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);
                
            """).replace("*N*", "{}".format(i+1)).format(i+1, self.n_HW_loop)
        self.sequence += textwrap.dedent("""\
            }
            """)
        
    def update_params(self):
        super().update_params()
        if self.trigger_mode == "None":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.waveform_buffer)
        elif self.trigger_mode == "Send Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.waveform_buffer)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
        self.waveform_buffer_samples = self.time_to_cycles(self.waveform_buffer, wait_time=False) // 16 * 16  # multiple of 16

    def replace_params(self):
        super().replace_params()
        self.sequence = self.sequence.replace("_BUFFER_", str(self.waveform_buffer_samples))

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - self.waveform_buffer) < 0:
            raise ValueError("Wait time cannot be negative!")

@attrs
class RabiSequence(Sequence):
    pulse_amplitudes = attrib(default=np.array([1.0]), validator=amp_smaller_1)
    pulse_width = attrib(default=50e-9, validator=is_positive)
    pulse_truncation = attrib(default=3, validator=is_positive)

    def write_sequence(self):
        self.sequence = textwrap.dedent("""\
            // Rabi Sequence
            
            wave w_1 = gauss(_GAUSS-PARAMS_);
            wave w_2 = drag(_GAUSS-PARAMS_);
            
        """)
        self.sequence += textwrap.dedent("""\
        repeat(_LOOP_){

        """)
        for i, amp in enumerate(self.pulse_amplitudes):
            self.sequence += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_);
                _TRIGGER-COMMAND-2_
                playWave({}*w_1, {}*w_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);

            """).format(i+1, len(self.pulse_amplitudes), amp, amp)
        self.sequence += textwrap.dedent("""\
        }
        """)

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.pulse_amplitudes)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in ["None", "Send Trigger"]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time) - self.gauss_params[0]/8
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)

    def replace_params(self):
        super().replace_params()
        self.sequence = self.sequence.replace("_GAUSS-PARAMS_", ",".join([str(p) for p in self.gauss_params]))

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - 2*self.pulse_width*self.pulse_truncation) < 0:
            raise ValueError("Wait time cannot be negative!")
        if self.n_HW_loop < len(self.pulse_amplitudes):
            raise ValueError("Length of hardware loop too long for number of specified amplitudes!")
        
@attrs
class T1Sequence(Sequence):
    pulse_amplitude = attrib(default=1, validator=amp_smaller_1)
    pulse_width = attrib(default=50e-9, validator=is_positive)
    pulse_truncation = attrib(default=3, validator=is_positive)
    delay_times = attrib(default=np.array([1e-6]))

    def write_sequence(self):
        self.sequence = textwrap.dedent("""\
            // T1 Sequence
            
            wave w_1 = {} * gauss(_GAUSS-PARAMS_);
            wave w_2 = {} * drag(_GAUSS-PARAMS_);
            
        """).format(self.pulse_amplitude, self.pulse_amplitude)
        self.sequence += textwrap.dedent("""\
        repeat(_LOOP_){

        """)
        for i, t in enumerate([self.time_to_cycles(t) for t in self.delay_times]):
            self.sequence += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_ - {});
                _TRIGGER-COMMAND-2_
                playWave(w_1, w_2);
                waitWave();
                wait(_WAIT-CYCLES-2_ + {});

            """).format(i+1, len(self.delay_times), t, t)
        self.sequence += textwrap.dedent("""\
        }
        """)

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.delay_times)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in ["None", "Send Trigger"]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time) - self.gauss_params[0]/8
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)

    def replace_params(self):
        super().replace_params()
        self.sequence = self.sequence.replace("_GAUSS-PARAMS_", ",".join([str(p) for p in self.gauss_params]))

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - self.gauss_params[0]/self.clock_rate) < 0:
            raise ValueError("Wait time cannot be negative!")
        if self.n_HW_loop > len(self.delay_times):
            raise ValueError("Length of hardware loop too long for number of specified delay times!")
        
@attrs
class T2Sequence(T1Sequence):
    def write_sequence(self):
        self.sequence = textwrap.dedent("""\
            // T2* Sequence
            
            wave w_1 = 0.5 * {} * gauss(_GAUSS-PARAMS_);
            wave w_2 = 0.5 * {} * drag(_GAUSS-PARAMS_);
            
        """).format(self.pulse_amplitude, self.pulse_amplitude)
        self.sequence += textwrap.dedent("""\
        repeat(_LOOP_){

        """)
        playWave_latency = 10e-9
        for i, t in enumerate([self.time_to_cycles(t) for t in (self.delay_times-playWave_latency)]):
            self.sequence += textwrap.dedent("""\
                // waveform {} / {}
                _TRIGGER-COMMAND-1_
                wait(_WAIT-CYCLES-1_ - {});
                _TRIGGER-COMMAND-2_
                playWave(w_1, w_2);
                wait({});
                playWave(w_1, w_2);
                waitWave();
                wait(_WAIT-CYCLES-2_);

            """).format(i+1, len(self.delay_times), t, t)
        self.sequence += textwrap.dedent("""\
        }
        """)



    



#################################################################
if __name__ == "__main__":
    pass