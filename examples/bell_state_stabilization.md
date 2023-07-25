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

# Bell State Stabilization

In this example we illustrate how to perform Bell state stabilization with real-time feedback using Zurich Instruments PQSC, SHFQA and SHFSG.

Requirements:
- LabOne Version >= 23.06
- 1 SHFQA
- 1 SHFSG
- 1 PQSC
- ZSync connections between the PQSC and the SHFQA and between the PQSC and the SHFSG
- Loopback connection between input and output of the first channel of the SHFQA

----

Bell states are the simplest examples of entangled states in a two-qubit system, and they are relevant for a multitude of quantum application. For instance, they can be used as an elementary unit of a complex error correction protocol, or be applied in quantum teleportation and quantum cryptography. There are four Bell states, also called maximally entangled states, but in this example we will use for illustrative purposes only one of them: $$|\psi ^{00} \rangle = \frac{|00 \rangle + |11 \rangle}{\sqrt{2}}$$

When talking about Bell states, the concepts of *bit parity* and *phase parity* play an important role: the bit parity of a Bell state is 0 if the qubits appear in the same state and 1 otherwise, while the phase parity refers to the relative phase appearing in the state superposition, being 0 if the phase is 0 and 1 if the phase is $\pi$. The Bell state written above has both bit parity and phase parity equal to 0, and is therefore called $|\psi ^{00} \rangle$. We can also call the bit parity *Z-Z parity* and the phase parity *X-X parity*.

Bell state stabilization is a procedure to preserve a two-qubit system in a Bell state by detecting and correcting possible errors that might have corrupted the state. Real-time stabilization can be achieved using an active feedback loop, which consists of three steps:
1. Perform bit and phase parity measurement using ancilla qubits to not make the Bell state collapse.
2. Apply a feedback operation conditioned on the outcome of the parity measurements.
3. Reset the ancilla qubits to the initial state to start a new round of stabilization.

We will assume that the ancilla qubits are entangled with the data qubits in a way such that measuring the first ancilla gives the value of the bit parity of the Bell state, and measuring the second ancilla gives the value of the phase parity. For more details about how to entangle ancilla and data qubits to achieve this, please refer to [this blog post](https://www.zhinst.com/ch/en/blogs/bell-state-stabilization-superconducting-qubits-real-time-feedback). We will also call the two ancillas "Z ancilla" and "X ancilla" because they measure respectively the Z-Z parity and the X-X parity. If both the parity and the phase are 0, the state is already stabilized; if the bit parity is 1, then a bit flip on one of the two data qubits has occurred, which can be corrected by applying a Z gate to either of the two qubits; if the phase parity is 1, then a phase flip has occurred, which can be corrected by applying a Z gate on either of the two qubits.

In this notebook we show how to perform the readout of the ancilla qubits with the SHFQA, how to apply the conditional gates with the SHFSG and how to use the PQSC to forward the result of the readout from teh SHFQA to the SHFSG.

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
Configure clock resources such that the PQSC receives the reference clock by an external source, and then distributes it to the other devices via ZSync connections.

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
SG_CHANNELS = [0,1,2,3]

# List of SG synthesizers
SG_SYNTHS = set([shfsg.sgchannels[sg_channel].synthesizer() for sg_channel in SG_CHANNELS])

with session.set_transaction():
    # SHFQA
    shfqa.qachannels[QA_CHANNEL].centerfreq(1e9)        # Hz
    shfqa.qachannels[QA_CHANNEL].input.range(0.0)       # dBm
    shfqa.qachannels[QA_CHANNEL].output.range(0.0)      # dBm
    shfqa.qachannels[QA_CHANNEL].mode("readout")
    shfqa.qachannels[QA_CHANNEL].input.on(True)
    shfqa.qachannels[QA_CHANNEL].output.on(True)

    # SHFSG synthesizers
    for sg_synth in SG_SYNTHS:
        shfsg.synthesizers[sg_synth].centerfreq(1e9)    # Hz

    # SHFSG
    for sg_channel in SG_CHANNELS:
        shfsg.sgchannels[sg_channel].awg.diozsyncswitch("zsync")
        shfsg.sgchannels[sg_channel].output.range(0.0)   # dBm
        shfsg.sgchannels[sg_channel].output.on(True)

    # PQSC - Replicate ZSync triggers on trigger output port
    pqsc.triggers.out[0].enable(True)
    pqsc.triggers.out[0].source("start_trigger")
    pqsc.triggers.out[0].port(pqsc.find_zsync_worker_port(shfsg))
```

```python
# Sample rate of the SHFQA and SHFSG waveform generator
SAMPLE_RATE = 2e9
```

## Configure ancilla qubit readout

The first thing that we have to do is to configure how to perform the readout of the ancilla qubits. For illustrative purposes, in this example we simulate one readout with no errors, one readout with a bit flip error and one readout with a phase flip error, for a total of 3 simulated readouts.

To perform a simulated qubit readout we connect the signal output of the SHFQA to its signal input in a closed loop. We then mimic the qubit state-dependent resonator response by using two different readout pulses for simulating a qubit in state $|0\rangle$ and in state $|1\rangle$. In particular, the two readout pulses will be both sinusoidal, but with a phase difference of 180 degrees so that the results of the integration will be maximally distant on the complex plane. We also set a common global phase $R$ to the pulses in order to have the complex results of the integration lie on the real axis; the value of $R$ that satisfies this can be measured for example with the Measurement Readout Result Tab in the LabOne Web Interface.

```python
NUM_READOUTS = 3  # Simulate 3 readouts
READOUT_REGISTER = 1  # Address of PQSC readout register
```

Define the readout pulses for the two ancillary qubits.

```python
# Readout pulses parameters
PULSE_DURATION = 126e-9
FREQUENCY_Z = 100e6  # Readout frequency for Z ancilla
FREQUENCY_X = -97e6  # Readout frequency for X ancilla
ROTATION_ANGLE_Z = np.deg2rad(55)  # Must be measured beforehand
ROTATION_ANGLE_X = np.deg2rad(55)  # Must be measured beforehand

pulse_len = int(PULSE_DURATION * SAMPLE_RATE)
time_vec = np.linspace(0, PULSE_DURATION, pulse_len)

# Define and upload waveforms
# Z ancilla
wave_0Z = 0.5 * np.exp(2j * np.pi * (FREQUENCY_Z * time_vec) + 1j * ROTATION_ANGLE_Z)
wave_1Z = 0.5 * np.exp(
    2j * np.pi * (FREQUENCY_Z * time_vec + 0.5) + 1j * ROTATION_ANGLE_Z
)
# X ancilla
wave_0X = 0.5 * np.exp(2j * np.pi * (FREQUENCY_X * time_vec) + 1j * ROTATION_ANGLE_X)
wave_1X = 0.5 * np.exp(
    2j * np.pi * (FREQUENCY_X * time_vec + 0.5) + 1j * ROTATION_ANGLE_X
)

readout_pulses = tk.Waveforms()
readout_pulses = tk.Waveforms()
readout_pulses[0] = wave_0Z
readout_pulses[1] = wave_1Z
readout_pulses[2] = wave_0X
readout_pulses[3] = wave_1X
shfqa.qachannels[QA_CHANNEL].generator.write_to_waveform_memory(readout_pulses)
```

Define the integration weights for the readout.

```python
weights = tk.Waveforms()
weights[0] = np.conj(np.exp(2j * np.pi * FREQUENCY_Z * time_vec))
weights[1] = np.conj(np.exp(2j * np.pi * FREQUENCY_X * time_vec))

shfqa.qachannels[QA_CHANNEL].readout.write_integration_weights(
    weights=weights,
    # Compensation for the delay between generator output and input
    # of the integration unit (short cable). This can be measured
    # experimentally.
    integration_delay=234e-9,
)
```

Configure the result logger to give us either 0 or 1, i.e. to perform state discrimination.

```python
with session.set_transaction():
    shfqa.qachannels[QA_CHANNEL].readout.result.length(NUM_READOUTS)
    shfqa.qachannels[QA_CHANNEL].readout.result.averages(1)
    shfqa.qachannels[QA_CHANNEL].readout.result.source("result_of_discrimination")

    shfqa.qachannels[QA_CHANNEL].readout.discriminators[0].threshold(0.0)
    shfqa.qachannels[QA_CHANNEL].readout.discriminators[1].threshold(0.0)
```

Finally, we configure the SHFQA to perform three readouts. The first readout should have result 00, simulating no error; the second readout should have result 10, simulating a bit flip error, and the third readout shoudl have result 01, simulating a phase flip error. Each readout starts after receiving a starting trigger over ZSync from the PQSC, and after each readout the result is forwarded to an address of the Readout Register Bank of the PQSC.

We set up the experiment by writing a sequencer program for the SHFQA. In particular, each readout is configured through the arguments of the function `startQA()`; for this experiment the following parameters are particularly relevant: 
- The first argument of `startQA()` is in the form `QA_GEN_i`, where `i` is the index of the waveform in the waveform memory to be played. Multiple waveforms can be played at the same time by combining them with the `| `operator, for example `QA_GEN_0 | QA_GEN_1`.
- The second argument of `startQA()` is in the form `QA_INT_i`, where `i` is the index of the weight in the integration weights memory to be used during integration. Multiple units can be triggered at the same time by combining them with the `| `operator, for example `QA_INT_0 | QA_INT_1`.
- The third argument is a flag to trigger the scope with the readout.
- The fourth argument of `startQA()` is the address of the PQSC readout register where the result of the readout is sent.

```python
seqc_program = tk.Sequence()

seqc_program.constants["num_cycles"] = NUM_READOUTS // 3
seqc_program.constants["READOUT_REGISTER"] = READOUT_REGISTER
seqc_program.constants["INT_LEN"] = int(np.ceil(pulse_len/16)*16)

seqc_program.code = textwrap.dedent(
    """\
    const NO_ERROR = QA_GEN_0|QA_GEN_2;         // Generator mask to simulate no error (outcome 00)
    const BIT_ERROR = QA_GEN_1|QA_GEN_2;        // Generator mask to simulate bit error (outcome 10)
    const PHASE_ERROR = QA_GEN_0|QA_GEN_3;      // Generator mask to simulate phase error (outcome 01)
    const INT_MASK = QA_INT_0|QA_INT_1;         // Integration mask

    repeat(num_cycles) {
        waitZSyncTrigger();                                      // Wait for start trigger
        playZero(INT_LEN);
        startQA(NO_ERROR, INT_MASK, true, READOUT_REGISTER);     // Generate a readout with no error

        waitZSyncTrigger();
        playZero(INT_LEN);
        startQA(BIT_ERROR, INT_MASK, true, READOUT_REGISTER);    // Simulate readout with bit error

        waitZSyncTrigger();
        playZero(INT_LEN);
        startQA(PHASE_ERROR, INT_MASK, true, READOUT_REGISTER);  // Simulate readout with phase error
    }
"""
)
shfqa.qachannels[QA_CHANNEL].generator.load_sequencer_program(seqc_program)
```

## Configure PQSC feedback
As metioned at the beginning, the PQSC is used to forward the result of the readout to the SHFSG with minimal latency.

The PQSC has a special memory bank called Readout Register Bank, which can store readout results measured by a Quantum Analyzer such as the SHFQA. Then, the data in the Readout Register Bank goes through a feedback pipeline which ends with signals being sent over ZSync outputs to other devices. This feedback pipeline has two modes of operation:
- *Register forwarding*: the a portion of the Readout Register Bank is directly forwarded as it is to a ZSync output port, without intermediate processing.
- *Decoder Unit*: the data from the Readout Register Bank is processed in the so-called Decoder Unit and the output of this processing is send to a ZSync output port. The data processing is programmed by configuring a look-up table (LUT).

In this experiment we show how to use the Decoder Unit to send to the SHFSG a processed version of the readout results. In particular, the entries of the Decoder look-up table will correspond to the feedback actions to be applied conditioned on the readout results. Since we have two ancilla qubits, there are $2^2 = 4$ possible outcomes of the readout and therefore the look-up table will have 4 entries.

***
**NOTE**

By default, the inputs of the LUT are configured to the readout register zero at index zero. That means, whenever such register/index is updated, all the unconfigured bits will get this value as input. Therefore, to avoid spurious input values, is strongly advised to not use the readout register zero when operating the LUT, so that it will never trigger any operation and it will read always zero. If the readout register zero is required, is advised to program all input bits of the LUT and the full LUT to avoid undefined behaviour.
***


Firstly, program the LUT.

```python
with session.set_transaction():
    # Source of bit 0 of LUT
    pqsc.feedback.decoder.lut.sources[0].register(READOUT_REGISTER)
    pqsc.feedback.decoder.lut.sources[0].index(0)
    # Source of bit 1 of LUT
    pqsc.feedback.decoder.lut.sources[1].register(READOUT_REGISTER)
    pqsc.feedback.decoder.lut.sources[1].index(1)

    # Output values of LUT
    lut = np.array([0, 1, 2, 3], dtype=np.uint32)
    pqsc.feedback.decoder.lut.tables[0](lut)
```

Then find the index of the ZSync port connected to the SHFSG.


And finally enable the Decoder Unit.

```python
# Find SHFSG ZSync port ID
shfsg_zsync_port = pqsc.find_zsync_worker_port(shfsg)

with session.set_transaction():
    # Enable Decoder Unit
    pqsc.zsyncs[shfsg_zsync_port].output.source("decoder")  # Enable Decoder
    pqsc.zsyncs[shfsg_zsync_port].output.enable(True)       # Enable ZSync feedback
    pqsc.zsyncs[shfsg_zsync_port].output.decoder.source(0)  # Index of LUT being forwarded
```

## Configure the SHFSG


### Feedback latency

For the last step of the experiment we configure the SHFSG to acquire the data received by the PQSC over ZSync and play a pulse conditioned on the received data. 

The tricky part here is that we have to tell the SHFSG *when* to read the result of the readout on the ZSync connection, but the we don't know a priori when the PQSC will send the result of the readout to the SHFSG. We need therefore a way to find out the so called *feedback latency*, i.e. the latency between the start trigger and the moment when data is sent over the ZSync connection to the SHFSG. 

Zurich Instruments `zhinst-utils` package provides a routine for calculating the feedback latency of a setup according to a model of the feedback system. The only thing that we have to calculate by ourselves and provide as a parameter to the routine is the latency accumulated in the readout (or "QA") stage, which is experiment-specific and therefore cannot be known in advance by the model. Such QA latency must include the integration length and any other delay defined by the user in the SHFQA seqC program before or after the readout.

```python
from zhinst.utils.feedback_model import (
    QCCSFeedbackModel,
    get_feedback_system_description,
    SGType,
    QAType,
    PQSCMode,
)

# Instantiate the class for the feedback model
feedback_model = QCCSFeedbackModel(
    description=get_feedback_system_description(
        generator_type=SGType.SHFSG,
        analyzer_type=QAType.SHFQA,
        pqsc_mode=PQSCMode.DECODER,
    )
)

# Calculate the QA delay in unit of samples (2 GHz or 500 ps steps)
int_len = shfqa.qachannels[QA_CHANNEL].readout.integration.length()
int_delay = round(
    shfqa.qachannels[QA_CHANNEL].readout.integration.delay() * SAMPLE_RATE
)
qa_delay = int_len + int_delay

# Get the total feedback latency in unit of sequencer clock cyles (250 MHz or 4 ns steps)
feedback_latency = feedback_model.get_latency(qa_delay)
```

### Define SeqC program and Command Table
Finally, we configure the error correction pulses that the SHFSG should apply. We have to apply gates both to the data qubits (to correct the errors) and to the ancilla qubits (to reset them in the initial state), for a total of 4 qubits. Therefore, we use 4 AWG cores.

```python
data_A_awg = shfsg.sgchannels[0].awg
data_B_awg = shfsg.sgchannels[1].awg
ancilla_x_awg = shfsg.sgchannels[2].awg
ancilla_z_awg = shfsg.sgchannels[3].awg
```

The output of the Decoder Unit sent over ZSync is always an 8-bit number, but the SHFSG will only need to look at the two least significant bits. Even more precisely, each AWG core will have to look at only one of these two bits: for the first data qubit and the Z ancilla only the second least significant bit is relevant, while for the second data qubit and the X ancilla only the least significant bit is relevant. (You can find very clear pictures in [this blog post](https://www.zhinst.com/ch/en/blogs/bell-state-stabilization-superconducting-qubits-real-time-feedback)).

In the following lines we tell each AWG cores which bits to read. The data is processed by the sequencer according to the following formula:

```
feedback_data = ((zsync_raw_message >> shift) & mask) + offset
```

so to look at the least significant bit we need to shift by zero positions, mask the last bit (mask = 0b0001) and add no offset; to look at the second least significant bit we need to shift by one positions, mask the last bit (mask = 0b0001) and add no offset.

```python
with session.set_transaction():
    data_A_awg.zsync.decoder.shift(1)
    data_A_awg.zsync.decoder.mask(0b1)
    data_A_awg.zsync.decoder.offset(0)

    data_B_awg.zsync.decoder.shift(0)
    data_B_awg.zsync.decoder.mask(0b1)
    data_B_awg.zsync.decoder.offset(0)

    ancilla_x_awg.zsync.decoder.shift(1)
    ancilla_x_awg.zsync.decoder.mask(0b1)
    ancilla_x_awg.zsync.decoder.offset(0)

    ancilla_z_awg.zsync.decoder.shift(0)
    ancilla_z_awg.zsync.decoder.mask(0b1)
    ancilla_z_awg.zsync.decoder.offset(0)
```

Lastly, we write the sequencer program and the command table for the SHFSG. With the following instruction:

`executeTableEntry(ZSYNC_DATA_PQSC_DECODER, feedback_latency);`

The Decoder data will be read after waiting for the feedback latency, and it will be directly forwarded to the command table without going through the sequencer. The command table will then execute the table entry corresponding to the bit read from the Decoder data. For illustrative purposes, to distinguish between X gate and Z gate we define two sequencer programs that differ only for the duration of the pulse. 

```python
seqc_X = tk.Sequence()

# Contants
constants = {
    "NUM_READOUTS": NUM_READOUTS,
    "feedback_latency": feedback_latency,
}
seqc_X.constants = constants

# Waveform
seqc_X.waveforms = tk.Waveforms()
seqc_X.waveforms[0] = 1.0 * np.ones(128)  # Short pulse = X gate

# Code
seqc_X.code = textwrap.dedent(
    """\
    repeat(NUM_READOUTS) {
        waitZSyncTrigger();
        executeTableEntry(ZSYNC_DATA_PQSC_DECODER, feedback_latency);
    }
"""
)
```

```python
seqc_Z = tk.Sequence()

seqc_Z.constants = constants

# Waveform
seqc_Z.waveforms = tk.Waveforms()
seqc_Z.waveforms[0] = 1.0 * np.ones(256)  # Long pulse = Z gate

# Code
seqc_Z.code = textwrap.dedent(
    """\
    repeat(NUM_READOUTS) {
        waitZSyncTrigger();
        executeTableEntry(ZSYNC_DATA_PQSC_DECODER, feedback_latency);
    }
"""
)
```

Command Table. Here every qubit will need the same command table, so we only write one command table and we will then upload it to every AWG core.

```python
ct_schema = shfsg.sgchannels[0].awg.commandtable.load_validation_schema()
ct = tk.CommandTable(ct_schema)

# Play a zero pulse (here 0.2 just for better visualization)
ct.table[0].waveform.index = 0
ct.table[0].amplitude00.value = 0.2
ct.table[0].amplitude01.value = -0.2
ct.table[0].amplitude10.value = 0.2
ct.table[0].amplitude11.value = 0.2

# Play a one pulse (here 0.5 just for better visualization)
ct.table[1].waveform.index = 0
ct.table[1].amplitude00.value = 1.0
ct.table[1].amplitude01.value = -1.0
ct.table[1].amplitude10.value = 1.0
ct.table[1].amplitude11.value = 1.0
```

Upload the sequencer program, the waveform and the command table to each AWG core.

```python
with session.set_transaction():
    # Apply X gate on data qubit A and on the ancilla qubits
    for awg_core in [data_A_awg, ancilla_x_awg, ancilla_z_awg]:
        awg_core.load_sequencer_program(seqc_X)
        awg_core.write_to_waveform_memory(seqc_X.waveforms)
        awg_core.commandtable.upload_to_device(ct)

    # Apply Z gate on data qubit B
    data_B_awg.load_sequencer_program(seqc_Z)
    data_B_awg.write_to_waveform_memory(seqc_Z.waveforms)
    data_B_awg.commandtable.upload_to_device(ct)
```

## Run experiment

```python
# Use the RT Logger to print a nice log of all the ZSync signals arriving to the SHFSG
import rtlogger_helpers

with session.set_transaction():
    # Reset RT Loggers
    for awg_core in [data_A_awg, data_B_awg, ancilla_x_awg, ancilla_z_awg]:
        rtlogger_helpers.reset_and_enable_rtlogger(awg_core)
    # Prepare the PQSC for triggering
    pqsc.arm(repetitions=NUM_READOUTS, holdoff=4e-6)
    # Enable SHFQA readout
    shfqa.qachannels[QA_CHANNEL].readout.result.enable(True)


# Enable the AWG cores
for awg_core in [data_A_awg, data_B_awg, ancilla_x_awg, ancilla_z_awg]:
    awg_core.enable_sequencer(single=True)

# Enable SHFQA readout pulse generator and check return value
assert shfqa.qachannels[QA_CHANNEL].generator.enable(True, deep=True)

# Run the PQSC. Start triggering and forward feedback
pqsc.execution.enable(True, deep=True)

# Wait until the sequencers report that their execution is done
for awg_core in [data_A_awg, data_B_awg, ancilla_x_awg, ancilla_z_awg]:
    awg_core.wait_done()
```

```python
print("------------------------------- Data qubit A -------------------------------")
rtlogger_helpers.print_rtlogger_data(session, data_A_awg)
print("------------------------------- Data qubit B -------------------------------")
rtlogger_helpers.print_rtlogger_data(session, data_B_awg)
print("----------------------------- Ancilla qubit X ------------------------------")
rtlogger_helpers.print_rtlogger_data(session, ancilla_x_awg)
print("----------------------------- Ancilla qubit Z ------------------------------")
rtlogger_helpers.print_rtlogger_data(session, ancilla_z_awg)
```
