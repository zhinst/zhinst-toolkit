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
    """SequenceProgram class that holds information about an AWG sequence.
    The class holds a Sequence object, depending on the set type of the sequence.
    the get() method returns the generated string for the seqC program that can 
    be downloaded to the AWG.
    
    Typical Usage:

        s = SequenceProgram()
        s.set(sequence_type="T1")
        s.set(delay_times=np.linspace(0, 10e-6, 11), period=20e-6, trigger_mode="Send Trigger")
        s.set(period=-1)
            > ValueError("Period must be positive!")
        
        s.list_params()
            > {'sequence_type': 'T1',
            >  'sequence_parameters': {'clock_rate': 2400000000.0,
            >  'period': 2e-05,
            >   ...

        print(s.get())
            > // Zurich Instruments sequencer program
            > // sequence type:              T1
            > // automatically generated:    20/12/2019 @10:47
            >
            > wave w_1 = 1 * gauss(720, 360, 120);
            > wave w_2 = 1 * drag(720, 360, 120);
            > ...
    
    """
    
    def __init__(self, sequence_type=None, **kwargs):
        self.__set_type(sequence_type)
        self.__sequence = self.sequence_class(**kwargs)        
    
    def get(self):
        return self.__sequence.get()

    def set(self, **settings):
        if "sequence_type" in settings:
            current_params = attr.asdict(self.__sequence)
            self.__init__(settings["sequence_type"])
            self.__sequence.set(**current_params) 
        self.__sequence.set(**settings)

    def list_params(self):
        return dict(
            sequence_type=self.sequence_type, 
            sequence_parameters=attr.asdict(self.__sequence)
        )

    def __set_type(self, type):
        if type == "None" or type is None:
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

#################################################################
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
        return self.sequence

    # main method to define sequence, will be overwritten
    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="None")

    def update_params(self):
        if self.trigger_mode == "None":
            self.trigger_cmd_1 = SeqCommand.comment_line()
            self.trigger_cmd_2 = SeqCommand.comment_line()
            self.dead_cycles = 0 
        elif self.trigger_mode == "Send Trigger":
            self.trigger_cmd_1 = SeqCommand.trigger(1)
            self.trigger_cmd_2 = SeqCommand.trigger(0)
            self.dead_cycles = self.time_to_cycles(self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.trigger_cmd_1 = SeqCommand.wait_dig_trigger()
            self.trigger_cmd_2 = SeqCommand.comment_line()
            self.dead_cycles = 0      

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

#################################################################
@attrs
class SimpleSequence(Sequence):
    buffer_lengths = attrib(default=[800], validator=attr.validators.instance_of(list))

    def write_sequence(self):            
        self.sequence = SeqCommand.header_comment(sequence_type="Simple")
        for i in range(self.n_HW_loop):
            self.sequence += SeqCommand.init_buffer_indexed(self.buffer_lengths[i], i)
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i in range(self.n_HW_loop):    
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            if self.trigger_mode == "External Trigger":
                temp = self.wait_cycles
            else:
                temp = self.wait_cycles - self.buffer_lengths[i]/8
            self.sequence += SeqCommand.wait(temp)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave_indexed(i)
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles)
            self.sequence += SeqCommand.new_line()
        self.sequence += SeqCommand.close_bracket()
        
    def update_params(self):
        super().update_params()
        if self.trigger_mode == "None":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "Send Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time)
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)
        if len(self.buffer_lengths) > self.n_HW_loop:
            self.n_HW_loop = len(self.buffer_lengths)

    def check_attributes(self):
        super().check_attributes()
        if len(self.buffer_lengths) != self.n_HW_loop:
            raise ValueError("Length of list buffer_lengths has to be equal to length of HW loop!")

#################################################################
@attrs
class RabiSequence(Sequence):
    pulse_amplitudes = attrib(default=np.array([1.0]), validator=amp_smaller_1)
    pulse_width = attrib(default=50e-9, validator=is_positive)
    pulse_truncation = attrib(default=3, validator=is_positive)

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="Rabi")
        self.sequence += SeqCommand.init_gauss(self.gauss_params)
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i, amp in enumerate(self.pulse_amplitudes):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            self.sequence += SeqCommand.wait(self.wait_cycles)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave_scaled(amp, amp)
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.pulse_amplitudes)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in ["None", "Send Trigger"]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time) - self.gauss_params[0]/8
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - 2*self.pulse_width*self.pulse_truncation) < 0:
            raise ValueError("Wait time cannot be negative!")
        if self.n_HW_loop < len(self.pulse_amplitudes):
            raise ValueError("Length of hardware loop too long for number of specified amplitudes!")

#################################################################
@attrs
class T1Sequence(Sequence):
    pulse_amplitude = attrib(default=1, validator=amp_smaller_1)
    pulse_width = attrib(default=50e-9, validator=is_positive)
    pulse_truncation = attrib(default=3, validator=is_positive)
    delay_times = attrib(default=np.array([1e-6]))

    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="T1")
        self.sequence += SeqCommand.init_gauss_scaled(self.pulse_amplitude, self.gauss_params)
        self.sequence += SeqCommand.repeat(self.repetitions)
        for i, t in enumerate(self.delay_times):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            self.sequence += SeqCommand.wait(self.wait_cycles - t)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave()
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles + t)
        self.sequence += SeqCommand.close_bracket()

    def update_params(self):
        super().update_params()
        self.n_HW_loop = len(self.delay_times)
        self.get_gauss_params(self.pulse_width, self.pulse_truncation)
        if self.trigger_mode in ["None", "Send Trigger"]:
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time) - self.gauss_params[0]/8
        elif self.trigger_mode == "External Trigger":
            self.wait_cycles = self.time_to_cycles(self.period - self.dead_time - self.latency + self.trigger_delay)

    def check_attributes(self):
        super().check_attributes()
        if (self.period - self.dead_time - self.gauss_params[0]/self.clock_rate) < 0:
            raise ValueError("Wait time cannot be negative!")
        if self.n_HW_loop > len(self.delay_times):
            raise ValueError("Length of hardware loop too long for number of specified delay times!")
        
#################################################################
@attrs
class T2Sequence(T1Sequence):
    def write_sequence(self):
        self.sequence = SeqCommand.header_comment(sequence_type="T2* (Ramsey)")
        self.sequence += SeqCommand.init_gauss_scaled(0.5 * self.pulse_amplitude, self.gauss_params)
        self.sequence += SeqCommand.repeat(self.repetitions)
        playWave_latency = 10e-9
        for i, t in enumerate([self.time_to_cycles(t) for t in (self.delay_times-playWave_latency)]):
            self.sequence += SeqCommand.count_waveform(i, self.n_HW_loop)
            self.sequence += self.trigger_cmd_1
            self.sequence += SeqCommand.wait(self.wait_cycles - t)
            self.sequence += self.trigger_cmd_2
            self.sequence += SeqCommand.play_wave()
            self.sequence += SeqCommand.wait(t)
            self.sequence += SeqCommand.play_wave()
            self.sequence += SeqCommand.wait_wave()
            self.sequence += SeqCommand.wait(self.dead_cycles)
        self.sequence += SeqCommand.close_bracket()  


#################################################################
if __name__ == "__main__":
    pass