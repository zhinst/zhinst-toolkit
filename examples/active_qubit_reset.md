---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.14.7
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# Active Qubit Reset


This tutorial shows how to perform an active qubit reset experiment with real-time feedback using Zurich Instruments PQSC, SHFQA and SHFSG devices.

Active qubit reset is a procedure to initialize a qubit in the ground state by measuring its state: if the qubit is measured in the excited state, then a $\pi$ pulse is applied to bring it in the ground state, while if the qubit is measured in the ground state then it's already initialized and there's nothing else to be done. In this example we will use the SHFQA to perform the readout of the qubit's state, the SHFSG to apply the conditional resetting pulse, and the PQSC to coordinate the experiment, enabling real-time feedback pulse with as little latency as possible.

Requirements:
- LabOne Version >= 23.06
- 1 SHFQA
- 1 SHFSG
- 1 PQSC
- ZSync connections between the PQSC and the SHFQA and between the PQSC and the SHFSG
- Loopback connection between input and output of the first channel of the SHFQA
----

```python
import zhinst.toolkit as tk
import numpy as np
import time, textwrap
```

## Connect to the devices


Create a session with a running Data Server, and then connect the Data Server with the instruments.

```python
shfqa_serial = "DEVXXXX"
shfsg_serial = "DEVYYYY"
pqsc_serial = "DEVZZZZ"

# Connect to the dataserver
session = tk.Session("localhost")

# Connect to the devices
shfqa = session.connect_device(shfqa_serial)
shfsg = session.connect_device(shfsg_serial)
pqsc = session.connect_device(pqsc_serial)

# Verify FW version compatibility
shfqa.check_compatibility()
shfsg.check_compatibility()
pqsc.check_compatibility()
```

```python
# Reset the devices to a known state
shfqa.factory_reset()
shfsg.factory_reset()
pqsc.factory_reset()
```

## Basic initial setup


### PQSC warmup
The PQSC needs 30 min to warmup. Before of this time, the skew between devices might be higher than expected. It's important to wait to perform any operation, because the faulty skew might persist after the warmup time otherwise.

```python
print("Waiting for stable clocks on PQSC... Might take up to 30 min.")
pqsc.system.clocks.ready.wait_for_state_change(1, timeout=60*30, sleep_time=1)
print("Clocks ready to operate the PQSC")
```


### Clocks and communications
The PQSC can either receive the clock from an external source, as shown in this example, or generate it internally. Then, the PQSC distributes the clock to the other devices via ZSync connections.

```python
# PQSC external reference clock (optional)
pqsc.system.clocks.referenceclock.in_.source("external")
pqsc.check_ref_clock()

# SHFSG and SHFQA ZSync clock
shfsg.system.clocks.referenceclock.in_.source("zsync")
shfqa.system.clocks.referenceclock.in_.source("zsync")

# Verify if the ZSync connection is successful
pqsc.check_zsync_connection([shfqa, shfsg])
```

### Inputs and outputs


Configure the basic settings for the SHFQA and SHFSG inputs and outputs, such as the range and the center frequency. For the PQSC we configure that the trigger signals sent over ZSync are replicated on the trigger output; the trigger output can then be connected to an oscilloscope to visualize the signals.

```python
# Default channels
QA_CHANNEL = 0
SG_CHANNEL = 0

SG_SYNTH = shfsg.sgchannels[SG_CHANNEL].synthesizer()

with session.set_transaction():
    # SHFQA
    shfqa.qachannels[QA_CHANNEL].centerfreq(1e9)    # Hz
    shfqa.qachannels[QA_CHANNEL].input.range(0.0)   # dBm
    shfqa.qachannels[QA_CHANNEL].output.range(0.0)  # dBm
    shfqa.qachannels[QA_CHANNEL].mode("readout")
    shfqa.qachannels[QA_CHANNEL].input.on(True)
    shfqa.qachannels[QA_CHANNEL].output.on(True)

    # SHFSG
    shfsg.sgchannels[SG_CHANNEL].awg.diozsyncswitch("zsync")
    shfsg.synthesizers[SG_SYNTH].centerfreq(1e9)    # Hz
    shfsg.sgchannels[SG_CHANNEL].output.range(0.0)  # dBm
    shfsg.sgchannels[SG_CHANNEL].output.on(True)

    # PQSC - Replicate ZSync triggers on trigger output port
    pqsc.triggers.out[0].enable(True)
    pqsc.triggers.out[0].source("start_trigger")
    pqsc.triggers.out[0].port(pqsc.find_zsync_worker_port(shfsg))
```

```python
# Sample rate of the SHFQA and SHFSG waveform generator
SAMPLE_RATE = 2e9
```

## Configure qubit readout

Now we start to dive into the steps of the experiment. The first step is to readout the state of the qubit with the SHFQA. For illustrative purposes, in this example we simulate a first readout with result 0, followed by a second readout with result 1.

To perform a simulated qubit readout we connect the signal output of the SHFQA to its signal input in a closed loop. We then mimic the qubit state-dependent resonator response by using two different readout pulses for simulating a qubit in state $|0\rangle$ and in state $|1\rangle$. In particular, the two readout pulses will be both sinusoidal, but with a phase difference of 180 degrees so that the results of the integration will be maximally distant on the complex plane. We also set a common global phase $R$ to the pulses in order to have the complex results of the integration lie on the real axis; the value of $R$ that satisfies this can be measured for example with the Measurement Readout Result Tab in the LabOne Web Interface.


We start by defining some parameters: `NUM_READOUTS`, corresponding to the number of pulses that will be sent; `INT_UNIT`, indicating the index of the integration unit of the SHFQA that should be used; `READOUT_REGISTER`, indicating the address of the Readout Register Bank on the PQSC where the SHFQA will eventually send the result of the readout.

```python
NUM_READOUTS = 2  # Simulate two events
INT_UNIT = 0  # Integration unit of the SHFQA
READOUT_REGISTER = 0  # Address of PQSC readout register
```

Next, define the two readout pulses and the integration weights such that the first readout returns 0 and the second readout returns 1. 

```python
# Readout pulses parameters
PULSE_DURATION = 126e-9
FREQUENCY = 100e6  # Readout frequency
ROTATION_ANGLE = np.deg2rad(55)  # Must be measured beforehand

pulse_len = int(PULSE_DURATION * SAMPLE_RATE)
time_vec = np.linspace(0, PULSE_DURATION, pulse_len)

# Define and upload waveforms
wave_0 = 0.5 * np.exp(2j * np.pi * (FREQUENCY * time_vec) + 1j * ROTATION_ANGLE)
wave_1 = 0.5 * np.exp(2j * np.pi * (FREQUENCY * time_vec + 0.5) + 1j * ROTATION_ANGLE)

readout_pulses = tk.Waveforms()
readout_pulses[0] = wave_0
readout_pulses[1] = wave_1

shfqa.qachannels[QA_CHANNEL].generator.write_to_waveform_memory(readout_pulses)
```

```python
weights = tk.Waveforms()
weights[INT_UNIT] = np.conj(np.exp(2j * np.pi * FREQUENCY * time_vec))

shfqa.qachannels[QA_CHANNEL].readout.write_integration_weights(
    weights=weights,
    # Compensation for the delay between generator output and input
    # of the integration unit (short cable). This can be measured
    # experimentally, for example using the Scope of the SHFQA.
    integration_delay=234e-9,
)
```

Configure the result logger of the SHFQA with the right number of readouts and configure the threshold for state discrimination.

```python
with session.set_transaction():
    shfqa.qachannels[QA_CHANNEL].readout.result.length(NUM_READOUTS)
    shfqa.qachannels[QA_CHANNEL].readout.result.averages(1)
    shfqa.qachannels[QA_CHANNEL].readout.result.source("result_of_discrimination")

    shfqa.qachannels[QA_CHANNEL].readout.discriminators[INT_UNIT].threshold(0.0)
```

Finally, we instruct the SHFQA on the steps that it should execute. We do this in a seqC program that will be uploaded to the SHFQA. 

In the seqC program, we tell the SHFQA to wait for a trigger signal to come from the PQSC over the ZSync connection. Once the trigger has come, the device starts the readout. Instructions about the readout are provided through the arguments of the function `startQA()`; for this experiment the following parameters are particularly relevant: 
- The first argument of `startQA()` is in the form `QA_GEN_i`, where `i` is the index of the waveform in the waveform memory to be played. Multiple waveforms can be played at the same time by combining them with the `| `operator, for example `QA_GEN_0 | QA_GEN_1`.
- The second argument of `startQA()` is in the form `QA_INT_i`, where `i` is the index of the weight in the integration weights memory to be used during integration. Multiple units can be triggered at the same time by combining them with the `| `operator, for example `QA_INT_0 | QA_INT_1`.
- The third argument is a flag to trigger the scope with the readout.
- The fourth argument of `startQA()` is the address of the PQSC readout register where the result of the readout is sent.


```python
seqc_program_shfqa = tk.Sequence()
seqc_program_shfqa.constants["QA_INT"] = f"QA_INT_{INT_UNIT}"
seqc_program_shfqa.constants["READOUT_REGISTER"] = READOUT_REGISTER
seqc_program_shfqa.constants["INT_LEN"] = int(np.ceil(pulse_len/16)*16)

seqc_program_shfqa.code = textwrap.dedent(
    """\
    const QBIT_0 = QA_GEN_0;    // Simulate qubit in 0 with waveform 0
    const QBIT_1 = QA_GEN_1;    // Simulate qubit in 1 with waveform 1

    waitZSyncTrigger();                                  // Wait for start trigger
    playZero(INT_LEN);
    startQA(QBIT_0, QA_INT, true, READOUT_REGISTER);     // Generate a readout = 0

    waitZSyncTrigger();
    playZero(INT_LEN);
    startQA(QBIT_1, QA_INT, true, READOUT_REGISTER);     // Generate a readout = 1
"""
)
shfqa.qachannels[QA_CHANNEL].generator.load_sequencer_program(seqc_program_shfqa)
```

## Configure PQSC feedback


As metioned earlier, the PQSC is used to forward the result of the readout to the SHFSG with minimal latency.

The PQSC has a special memory bank called Readout Register Bank, which can store readout results measured by a Quantum Analyzer such as the SHFQA. Then, the data in the Readout Register Bank goes through a feedback pipeline which ends with signals being sent over ZSync outputs to other devices. This feedback pipeline has two modes of operation:
- *Register forwarding*: the a portion of the Readout Register Bank is directly forwarded as it is to a ZSync output port, without intermediate processing.
- *Decoder Unit*: the data from the Readout Register Bank is processed in the so-called Decoder Unit and the output of this processing is send to a ZSync output port. The data processing is programmed by configuring a look-up table.

Here we configure the PQSC to do register forwarding of the result of the qubit readout to the SHFSG. Since we only need to forward one bit to the SHFSG, we only configure the first register forwarding unit (`sources[0]`) of the SHFSG ZSync output.

```python
# Find SHFSG ZSync port ID
shfsg_zsync_port = pqsc.find_zsync_worker_port(shfsg)

with session.set_transaction():
    # Enable Readout Register Bank forwarding to ZSync output
    pqsc.zsyncs[shfsg_zsync_port].output.source("register_forwarding")
    pqsc.zsyncs[shfsg_zsync_port].output.enable(True)
    # Enable forwarding to first result only
    pqsc.zsyncs[shfsg_zsync_port].output.registerbank.sources["*"].enable(False)
    pqsc.zsyncs[shfsg_zsync_port].output.registerbank.sources[0].enable(True)
    # The Readout Register being forwarded
    pqsc.zsyncs[shfsg_zsync_port].output.registerbank.sources[0].register(READOUT_REGISTER)
    # The index of the result in the readout register being forwarded
    # A result IN THE PQSC is defined as two integration units in the SHFQA
    pqsc.zsyncs[shfsg_zsync_port].output.registerbank.sources[0].index(INT_UNIT//2)
```

## Configure SHFSG


For the last step of the experiment we must instruct the SHFSG to acquire the result of the readout forwarded to it by the PQSC via ZSync, and then to play a pulse depending on the acquired value.

The tricky part here is that we have to tell the SHFSG *when* to read the result of the readout on the ZSync connection, but the we don't know a priori when the PQSC will send the result of the readout to the SHFSG. We need therefore a way to find out the so called *feedback latency*, i.e. the latency between the start trigger and the moment when data is sent over the ZSync connection to the SHFSG. There are two methods for finding the feedback latency:
- **RT Logger**: the Real-time Logger is a functionality for logging the history of received ZSync triggers and data. We can use it to measure the feedback latency and then hard-code this value when programming the SHFSG.

- **Model for feedback latency**: `zhinst.utils` exposes a function that calculates, according to the model of the PQSC feedback system, the feedback latency.

Using the model for the feedback latency is recommended because of stability reasons, and because it has been extensively tested. However, the RT logger is a useful tool for monitoring the signals that reach the SHFSG. For this reason, we now illustrate how to use both methods.


### Data processing

The PQSC sends up to eight readout results at the same time. Each is made by two qubit readout results, or by one qutrit/ququad result. We need to configure the SHFSG to look only at the one interesting for us; depending on the integration unit used, it will be in the least significant bit (if INT_UNIT mod 2  is zero) or in the second to last significant otherwise. The data is processed by the sequencer according to the following formula:

```
feedback_data = ((zsync_raw_message >> shift) & mask) + offset
```

so we need to shift by zero or one positions, mask the last bit (mask = 0b0001) and add no offset.

```python
with session.set_transaction():
    shfsg.sgchannels[SG_CHANNEL].awg.zsync.register.shift(INT_UNIT%2)
    shfsg.sgchannels[SG_CHANNEL].awg.zsync.register.mask(0b0001)
    shfsg.sgchannels[SG_CHANNEL].awg.zsync.register.offset(0)
```

### RT Logger


Firstly, define a simple sequencer program for the SHFSG that just waits for the start trigger and does nothing else. This is needed, otherwise the RT Logger will not record any data.

```python
seqc_program_shfsg = tk.Sequence()
seqc_program_shfsg.constants["NUM_READOUTS"] = NUM_READOUTS
seqc_program_shfsg.code = textwrap.dedent(
    """\
    repeat(NUM_READOUTS) {
        waitZSyncTrigger();
    }
"""
)
shfsg.sgchannels[SG_CHANNEL].awg.load_sequencer_program(seqc_program_shfsg)
```

Then, enable the RT logger. It will listen for data received by the SHFSG on ZSync, and print it. Since the details of how to configure the RT logger are not the main point of this notebook, we have wrapped them in some functions contained in the `helpers.py` script.

```python
import rtlogger_helpers

rtlogger_helpers.reset_and_enable_rtlogger(shfsg.sgchannels[SG_CHANNEL].awg)
```

Now we can run all the instruments in the right order and print the RT Logger data. For convenience we wrap into a function the code for running the experiment, as we will be using it often.

```python
def run_active_reset():
    with session.set_transaction():
        # Reset RT Logger
        rtlogger_helpers.reset_and_enable_rtlogger(
            shfsg.sgchannels[SG_CHANNEL].awg
        )
        # Prepare the PQSC for triggering
        pqsc.arm(repetitions=NUM_READOUTS, holdoff=2e-6)
        # Enable SHFQA readout
        shfqa.qachannels[QA_CHANNEL].readout.result.enable(True)

    # Enable SHFQA readout pulse generator and SHFSG awg sequencer
    # Wait until both sequencers report that are running and waiting for triggers
    # or throw an error
    assert shfqa.qachannels[QA_CHANNEL].generator.enable(True, deep=True)
    assert shfsg.sgchannels[SG_CHANNEL].awg.enable(True, deep=True)

    # Run the PQSC. Start triggering and forward feedback
    pqsc.execution.enable(True, deep=True)

    # Wait until both sequencers report that their execution is done
    shfqa.qachannels[QA_CHANNEL].generator.enable.wait_for_state_change(False)
    shfsg.sgchannels[SG_CHANNEL].awg.enable.wait_for_state_change(False)


run_active_reset()

print("QA Result logger output")
shfqa.qachannels[QA_CHANNEL].readout.result.acquired.wait_for_state_change(NUM_READOUTS)
print(shfqa.qachannels[QA_CHANNEL].readout.result.data[INT_UNIT].wave())
print()

print("RTlogger output")
rtlogger_helpers.print_rtlogger_data(
    session, shfsg.sgchannels[SG_CHANNEL].awg, compensate_start_trigger=True
)
```

On the first column we see the timestamp of the data received by the SHFSG from the PQSC. The two lines with timestamp equal to 0 correspond to trigger events, which reset the time count. The other two lines correspond to the readout result being forwarded by the PQSC to the SHFSG, and the field `register` shows the value of the readout result (notice, as expected, that the readout data is 0 for the first readout and 1 for the second!).

The idea now is to use such timestamp to instruct the SHFSG when to read the ZSync data and perform active qubit reset!

We can now write a sequence where we use `getFeedback()` to acquire data at a specified time after the start trigger. With `ZSYNC_DATA_PQSC_REGISTER` as argument of `getFeedback()` we tell the sequencer to look at the data coming from the PQSC qubit readout register forwarding.

In the following sequencer code we also write the readout results to the user register of the SHFSG to double check that we read the correct data.

```python
feedback_latency = 181

seqc_program_shfsg = tk.Sequence()
seqc_program_shfsg.constants["feedback_latency"] = feedback_latency
seqc_program_shfsg.code = textwrap.dedent(
    """\
    var r1, r2;

    waitZSyncTrigger();
    r1 = getFeedback(ZSYNC_DATA_PQSC_REGISTER, feedback_latency);

    waitZSyncTrigger();
    r2 = getFeedback(ZSYNC_DATA_PQSC_REGISTER, feedback_latency);
    
    setUserReg(0, r1);
    setUserReg(1, r2);
"""
)
shfsg.sgchannels[SG_CHANNEL].awg.load_sequencer_program(seqc_program_shfsg)
```

Finally, we run again the experiment and check that the SHFSG has read the correct values.

```python
run_active_reset()

print("QA Result logger output")
shfqa.qachannels[QA_CHANNEL].readout.result.acquired.wait_for_state_change(NUM_READOUTS)
print(shfqa.qachannels[QA_CHANNEL].readout.result.data[INT_UNIT].wave())
print()

print(
    "First readout - expected result: 0 - actual result: ",
    shfsg.sgchannels[SG_CHANNEL].awg.userregs[0](deep=True)[1],
)
print(
    "Second readout - expected result: 1 - actual result: ",
    shfsg.sgchannels[SG_CHANNEL].awg.userregs[1](deep=True)[1],
)
```

### Model for feedback latency


As mentioned above, the RT Logger is useful for visualizing the events that happen during the experiment, but it's also tedious to configure and sometimes the timestamps of the logged events happen to be show a little jittering in different runs of the experiment. Moreover, the feedback latency has to be hardcoded into the sequencer program, which makes the method error prone if the feedback latency happens to change, for example because the integration time changes.

For this reason, the `zhinst.utils` package offers the class `QCCSFeedbackModel` for calculating the feedback latency. The advantage of this method is that it provides stable results for the feedback latency and that it has been extensively tested, therefore it can be considered highly reliable.

In order for the class to calculate the feedback latency, during its instantiation we have to describe the feedback system by telling the type of generator device (e.g. SHFSG or HDAWG), the type of quantum analyzer (e.g. SHFQA), and the PQSC mode (register forward or decoder). We can then use the function `get_latency()` to get the feedback latency. The only thing that we have to calculate by ourselves and provide to the routine is the latency accumulated in the readout (or "QA") stage, which is experiment-specific. Such QA latency must include the integration length, the integration delay and any other delay defined by the user in the SHFQA seqC program before or after the readout (not shown here).

```python
from zhinst.utils.feedback_model import (
    QCCSFeedbackModel,
    get_feedback_system_description,
    SGType,
    QAType,
    PQSCMode,
)

# Instantiate the class describing feedback system
feedback_model = QCCSFeedbackModel(
    description=get_feedback_system_description(
        generator_type=SGType.SHFSG,
        analyzer_type=QAType.SHFQA,
        pqsc_mode=PQSCMode.REGISTER_FORWARD,
    )
)

# Calculate delay of the readout stage in unit of samples (2 GHz or 500 ps steps)
int_len = shfqa.qachannels[QA_CHANNEL].readout.integration.length()
int_delay = round(
    shfqa.qachannels[QA_CHANNEL].readout.integration.delay() * SAMPLE_RATE
)
qa_delay = int_len + int_delay

# Get the feedback latency in unit of sequencer clock cyles (250 MHz or 4 ns steps)
feedback_latency = feedback_model.get_latency(qa_delay)

print(
    f"Feedback latency according to the feedback model: {feedback_latency} clock cycles."
)
```

It's as easy as that! Now we can do the same steps that we did for the RT Logger to check that the SHFSG reads the correct data, but this time using the feedback latency calculated with the model.

```python
seqc_program_shfsg = tk.Sequence()
seqc_program_shfsg.constants["feedback_latency"] = feedback_latency
seqc_program_shfsg.code = textwrap.dedent(
    """\
    var r1, r2;

    waitZSyncTrigger();
    r1 = getFeedback(ZSYNC_DATA_PQSC_REGISTER, feedback_latency);

    waitZSyncTrigger();
    r2 = getFeedback(ZSYNC_DATA_PQSC_REGISTER, feedback_latency);
    
    setUserReg(0, r1);
    setUserReg(1, r2);
"""
)
shfsg.sgchannels[SG_CHANNEL].awg.load_sequencer_program(seqc_program_shfsg)

run_active_reset()

print("QA Result logger output")
shfqa.qachannels[QA_CHANNEL].readout.result.acquired.wait_for_state_change(NUM_READOUTS)
print(shfqa.qachannels[QA_CHANNEL].readout.result.data[INT_UNIT].wave())
print()

print(
    "First readout - expected result: 0 - actual result: ",
    shfsg.sgchannels[SG_CHANNEL].awg.userregs[0](deep=True)[1],
)
print(
    "Second readout - expected result: 1 - actual result: ",
    shfsg.sgchannels[SG_CHANNEL].awg.userregs[1](deep=True)[1],
)
```

## Apply the conditional $\pi$ pulse


Finally, we can tell the SHFSG what pulses to play depending on the value of the received bit. We do this in the following way: we define a command table with entries `0` and `1`, describing the pulses that should be played if the qubit was measured respectively in $|0\rangle$ or in $|1\rangle$.

With the following instruction:

`executeTableEntry(ZSYNC_DATA_PQSC_REGISTER, feedback_latency);` 

the Decoder data will be read after waiting for the feedback latency, and it will be directly forwarded to the command table without going through the sequencer. The command table will then execute the table entry corresponding to the bit read from the Decoder data.

```python
# Define the sequencer program
seqc_program_shfsg = tk.Sequence()

# Constants
seqc_program_shfsg.constants["feedback_latency"] = feedback_latency
seqc_program_shfsg.constants["NUM_READOUTS"] = NUM_READOUTS

# Waveform
seqc_program_shfsg.waveforms = tk.Waveforms()
seqc_program_shfsg.waveforms[0] = 1.0 * np.ones(128)  # Just a simple square pulse

# Code
seqc_program_shfsg.code = textwrap.dedent(
    """\
    repeat(NUM_READOUTS) {
        waitZSyncTrigger();
        executeTableEntry(ZSYNC_DATA_PQSC_REGISTER, feedback_latency);
    }
"""
)
```

```python
# Define the command table
ct_schema = shfsg.sgchannels[SG_CHANNEL].awg.commandtable.load_validation_schema()
ct = tk.CommandTable(ct_schema)

# Qubit was in 0 state
# Play a 0.2 pulse (should be zero, just for better visualization)
ct.table[0].waveform.index = 0
ct.table[0].amplitude00.value = 0.2
ct.table[0].amplitude01.value = -0.2
ct.table[0].amplitude10.value = 0.2
ct.table[0].amplitude11.value = 0.2

# Qubit was in 1 state
# Play a 1.0 pulse
ct.table[1].waveform.index = 0
ct.table[1].amplitude00.value = 1.0
ct.table[1].amplitude01.value = -1.0
ct.table[1].amplitude10.value = 1.0
ct.table[1].amplitude11.value = 1.0
```

```python
# Upload sequence, waveforms and command table
with session.set_transaction():
    shfsg.sgchannels[SG_CHANNEL].awg.load_sequencer_program(seqc_program_shfsg)
    shfsg.sgchannels[SG_CHANNEL].awg.write_to_waveform_memory(
        seqc_program_shfsg.waveforms
    )
    shfsg.sgchannels[SG_CHANNEL].awg.commandtable.upload_to_device(ct)
```

## Run the experiment

```python
run_active_reset()

print("QA Result logger output")
shfqa.qachannels[QA_CHANNEL].readout.result.acquired.wait_for_state_change(NUM_READOUTS)
print(shfqa.qachannels[QA_CHANNEL].readout.result.data[INT_UNIT].wave())
print()

print("RTlogger output")
rtlogger_helpers.print_rtlogger_data(session, shfsg.sgchannels[SG_CHANNEL].awg)
```
