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

# Repeat-until-success

This tutorial shows how to perform a repeat-until-success experiment with real-time feedback using Zurich Instruments PQSC, SHFQA and SHFSG devices.

Repeat-until-success is a procedure to obtain a desired quantum state by repeatedly performing a sequence of gates on the qubits and then measuring their state, until the qubits are measured in the desired state. 

In this example we illustrate a very simple case of repeat-until-success, in which we repeatedly measure the state of a qubit until we we find it to be in the 1 state. In particular, we show how to perform real-time feedback of the measurement outcomes and how to engineer the timing of the experiment.

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

# Conversion factor from clock cycles to samples for SHFSG
CLOCK_TO_SAMPLE_SG = 8
```

## Configure readout pulses and weights

The first thing that we have to do is to configure how to perform the readout of the qubit. For illustrative purposes, in this example we simulate three readouts, of which the first two are failures (readout result 0) and the last one is a success (readout result 1).

To perform a simulated qubit readout we connect the signal output of the SHFQA to its signal input in a closed loop. We then mimic the qubit state-dependent resonator response by using two different readout pulses for simulating a qubit in state $|0\rangle$ and in state $|1\rangle$. In particular, the two readout pulses will be both sinusoidal, but with a phase difference of 180 degrees so that the results of the integration will be maximally distant on the complex plane. We also set a common global phase $R$ to the pulses in order to have the complex results of the integration lie on the real axis; the value of $R$ that satisfies this can be measured for example with the Measurement Readout Result Tab in the LabOne Web Interface.

```python
SIMULATED_FAILURES = 2
```

Define the readout pulses for the two ancillary qubits.

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

Define the integration weights for the readout.

```python
# Integration unit of the SHFQA
INT_UNIT = 0

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

Configure the result logger to give us either 0 or 1, i.e. to perform state discrimination.

```python
with session.set_transaction():
    shfqa.qachannels[QA_CHANNEL].readout.result.length(SIMULATED_FAILURES + 1)
    shfqa.qachannels[QA_CHANNEL].readout.result.averages(1)
    shfqa.qachannels[QA_CHANNEL].readout.result.source("result_of_discrimination")

    shfqa.qachannels[QA_CHANNEL].readout.discriminators[INT_UNIT].threshold(0.0)
```

## Configure the feedback

In the following part of the example we actually describe the steps of the experiment and, most importantly, their timing. 

The experiment will run as follows:
1. the PQSC sends a start trigger to the instruments to signal the beginning of the experiment;
2. the SHFSG plays a pulse indicating that a "try" segment is starting. Let us call this `try pulse`;
3. the SHFQA performs a readout and then sends the result to the PQSC readout register bank via ZSync;
4. the PQSC forwards the result to the SHFSG via ZSync with minimal latency;
5. the SHFSG plays a different "success" pulse if the readout result was 1 (success), otherwise it starts again from step 2.

Steps 2-5 are thus repeated until a success event happens. For illustrative purposes, in this example we simulate 2 failures (qubit measured in 0 state) and a final success (qubit measured in 1 state), but of course in a real experiment points 2-4 would be repeated indefinitely until a success happens.


### Calculate feedback latency and create timing grid

A crucial aspect of the experiment is the timing of the operations. In particular, there are two timing requirements that we should consider:
- at each iteration, the SHFQA should wait that the SHFSG has finished playing the try pulse, before starting the readout;
- after playing the try pulse the SHFSG must that new readout result is available on its ZSync input port, before reading it and doing the following actions;

The first timing requirement is easily fulfillable: given that the try pulse has length `WAVEFORM_TRY_LEN`, we can delay the SHFQA readout by using the seqC instruction `playZero(WAVEFORM_TRY_LEN)` before starting the readout. 

With respect to the second timing requirement, we use the seqC instruction `getFeedback` to read the readout result. This instruction takes as a parameter the delay (measured from the last start trigger) that the instrument should wait before reading the readout result. Our task is hence to estimate how long this delay should be and then provide it to the instrument through `getFeedback`. How do we estimate the right delay?

We call *feedback latency* the amount of time between the initial start trigger and the moment when the readout is available on the SHFSG ZSync input port. This latency depends on the time it takes to the Quantum Analyzer to complete the readout, but also on the time it takes for the result to go to the PQSC, be processed and then be sent to the SHFSG. The package `zhinst-utils` offers the class `QCCSFeedbackModel` which, given a description of the experiment setup, has a method `get_latency()` that calculates the feedback latency based on a model of the feedback system. The only argument that we have to provide to `get_latency()` is the latency accumulated by the operations in the Quantum Analyzer during the readout, which is experiment-specific and therefore cannot be known in advance by the model. We refer to this latency as `qa_delay`, and it includes for example the integration length or any other user-defined delays before the integration. 

So we can calculate the feedback latency with the model and then tell the SHFSG to wait for an amount of time equal to the feedback latency, before reading the readout result on ZSync.

But what about the iterations other than the first one? The delay to be waited that we pass to the seqC instruction `getFeedback` must always be measured starting from the initial start trigger. Hence, we would have to recalculate the feedback latency at each iteration to include the latency of all the previous cycles. However, we can take advantage of a fact regarding the feedback latency calculated by the model: 

`get_latency(qa_delay + N*200 ns) = get_latency(qa_delay) + N*200 ns`

with `N` integer. In other terms, if and only if the duration of one try cycle is an integer multiple of 200 ns (i.e. `N*200 ns`), then the new feedback latency at each iteration will be equal to the old feedback latency of the previous cycle plus the duration of a cycle! What does this imply? If we engineer the cycles in oder to last an integer multiple of 200 ns, we can avoid recalculating the feedback latency with the model at each iteration, and be much faster.

This may sound complicated at first, so let's have a look at the code.


As first thing we instantiate `QCCSFeedbackModel`, calculate `qa_delay` and the feedback latency of the first iteration.

```python
from zhinst.utils.feedback_model import (
    QCCSFeedbackModel,
    get_feedback_system_description,
    SGType,
    QAType,
    PQSCMode,
)

# Instantiate the class
feedback_model = QCCSFeedbackModel(
    description=get_feedback_system_description(
        generator_type=SGType.SHFSG,
        analyzer_type=QAType.SHFQA,
        pqsc_mode=PQSCMode.DECODER,
    )
)

# Length of the "try" waveform played by the SHFSG
# in unit of samples (2 GHz or 500 ps steps)
WAVEFORM_TRY_LEN = 128

# Delay in the QA stage in unit of samples (2 GHz or 500 ps steps)
# Look at the sequencer code below to match the delays
int_start = WAVEFORM_TRY_LEN
int_len = shfqa.qachannels[QA_CHANNEL].readout.integration.length()
int_delay = round(
    shfqa.qachannels[QA_CHANNEL].readout.integration.delay() * SAMPLE_RATE
)

qa_delay = int_start + int_len + int_delay

# Total feedback latency in unit of sequencer clock cyles (250 MHz or 4 ns steps)
feedback_latency = feedback_model.get_latency(qa_delay)
```

And now we enforce the duration of one SHFQA iteration to be a multiple of 200 ns. In technical jargon, we say that we create a *timing grid* with a spacing of 200 ns.

```python
GRID_SPACING = 200e-9
# Number of samples in 200 ns
grid_samples = SAMPLE_RATE * GRID_SPACING

# Number of clock cycles needed for evaluating while condition (found empirically)
LOOP_OVERHEAD = 8
# Duration of one iteration, expressed in number samples
cycle_len_samples = (feedback_latency + LOOP_OVERHEAD) * CLOCK_TO_SAMPLE_SG

# Increase the length of one cycle to reach the closest integer multiple of `grid_samples`
cycle_len_samples = int(np.ceil(cycle_len_samples / grid_samples) * grid_samples)
# Express the duration in clock cycles again (needed in the seqc program)
cycle_len_clocks = cycle_len_samples // CLOCK_TO_SAMPLE_SG

# Subtract the length of the `try` waveform to get the length of the `startQA` section
section_len = cycle_len_samples - WAVEFORM_TRY_LEN
```

## SHFQA sequencer program


Now instruct the SHFQA on what it should do and with which timing, by writing the instructions in a sequencer program. In particular, we tell the SHFQA to:
1. Stay silent for `WAVEFORM_TRY_LEN` samples, while the SHFSG plays the "try" waveform;
2. Start a section with a duration `section_len`, previously calculated such that `section_len + WAVEFORM_TRY_LEN` is an integer multiple of 200 ns;
3. During this section, perform the readout with `startQA` and forward the result of the readout to the PQSC readout register bank address specified by `READOUT_REGISTER`;
4. Update the feedback time for the next iteration.
These steps are repeated for `SIMULATED_FAILURES` times simulating a readout with result 0. Then we simulate an additional readout with result 1.

<u>Note 1</u>:
Instructions about the readout are provided through the arguments of the function `startQA()`; for this experiment the following parameters are particularly relevant: 
- The first argument of `startQA()` is in the form `QA_GEN_i`, where `i` is the index of the waveform in the waveform memory to be played. Multiple waveforms can be played at the same time by combining them with the `| `operator, for example `QA_GEN_0 | QA_GEN_1`.
- The second argument of `startQA()` is in the form `QA_INT_i`, where `i` is the index of the weight in the integration weights memory to be used during integration. Multiple units can be triggered at the same time by combining them with the `| `operator, for example `QA_INT_0 | QA_INT_1`.
- The third argument is a flag to trigger the scope with the readout.
- The fourth argument of `startQA()` is the address of the PQSC readout register where the result of the readout is sent.

<u>Note 2</u>: the way to force the duration of the readout section to be `section_len` is to execute a `playZero(section_len)` before `startQA`. This may seem confusing at first, but the reason why this works is that `playZero` can run in parallel with a `startQA` and will only block other `playZero`. In practice, this will force the duration of the readout section to be `section_len`.

```python
READOUT_REGISTER = 1  # Address of PQSC readout register

seqc_program_shfqa = tk.Sequence()

# Assign constants
constants = {
    "feedback_latency": feedback_latency,
    "SIMULATED_FAILURES": SIMULATED_FAILURES,
    "cycle_len_clocks": cycle_len_clocks,
    "READOUT_REGISTER": READOUT_REGISTER,
    "WAVEFORM_TRY_LEN": WAVEFORM_TRY_LEN,
    "section_len": section_len,
}
seqc_program_shfqa.constants = constants

seqc_program_shfqa.code = textwrap.dedent(
    """\
    var success;
    var feedback_time = feedback_latency;
    var remaining_failures = SIMULATED_FAILURES;

    waitZSyncTrigger();

    // Simulate failures
    do {
        playZero(WAVEFORM_TRY_LEN);                             // Do nothing while SHFSG plays "try" waveform
        playZero(section_len);                                  // Define the duration of the startQA section
        startQA(QA_GEN_0, QA_INT_0, true, READOUT_REGISTER);    // Simulate readout = 0

        success = getFeedback(ZSYNC_DATA_RAW, feedback_time);   // Result of the readout
        feedback_time += cycle_len_clocks;                      // Update feedback time for next iteration
        remaining_failures -= 1;
    } while (remaining_failures);

    // Final try (success)
    playZero(WAVEFORM_TRY_LEN);
    playZero(section_len);
    startQA(QA_GEN_1, QA_INT_0, true, READOUT_REGISTER);

    success = getFeedback(ZSYNC_DATA_RAW, feedback_time);
    feedback_time += cycle_len_clocks;
"""
)
shfqa.qachannels[QA_CHANNEL].generator.load_sequencer_program(seqc_program_shfqa)
```

## Configure PQSC
As metioned earlier, the PQSC is used to forward the result of the readout to the SHFSG with minimal latency.

The PQSC has a special memory bank called Readout Register Bank, which can store readout results measured by a Quantum Analyzer such as the SHFQA. Then, the data in the Readout Register Bank goes through a feedback pipeline which ends with signals being sent over ZSync outputs to other devices. This feedback pipeline has two modes of operation:
- *Register forwarding*: a portion of the Readout Register Bank is directly forwarded as it is to a ZSync output port, without intermediate processing.
- *Decoder Unit*: the data from the Readout Register Bank is processed in the so-called Decoder Unit and the output of this processing is sent to a ZSync output port. The data processing is programmed by configuring a look-up table.

<u>Note</u>: regardless of the operation mode of the feedback pipeline, the PQSC always sends on the ZSync outputs 4 bits coming from register forwarding and 8 bits coming from the Decoder Unit. It is our task to program the SHFSG to only consider the bits that are relevant for the experiment.

In this experiment we show how to use the Decoder Unit to send to the SHFSG a processed version of the readout results. In particular, we want the PQSC to send to the SHFSG the value 1 if the readout result was 0, and to send the value 0 if the readout result was 1. In this way the ZSync output value represents the happening of a failures rather than a success: let us call this value `failure`, as we will do later in the SHFSG sequencer program. The advantage of having a variable represeting this is that we directly do the loop "repeat-until-success" using this variable as an iterator with `while(failure)`. If we instead did register forwarding we would have a variable (let us imagine calling it `success`) representing whether a success has happened, and we would have to write the loop as `while(!success)`, which takes up more time that `while(failure)` because of the NOT operation. In other words, in this experiment we use the Decoder Unit to optimize the performance.

***
**NOTE**

By default, the inputs of the LUT are configured to the readout register zero at index zero. That means, whenever such register/index is updated, all the unconfigured bits will get this value as input. Therefore, to avoid spurious input values, is strongly advised to not use the readout register zero when operating the LUT, so that it will never trigger any operation and it will read always zero. If the readout register zero is required, is advised to program all input bits of the LUT and the full LUT to avoid undefined behaviour.
***


Firstly, configure the lookup table. Since we only want to forward one bit, we only configure bit 0 of the LUT.

```python
# Enable look-up table (LUT)
with session.set_transaction():
    pqsc.feedback.decoder.lut.sources[0].register(
        READOUT_REGISTER
    )  # Source register for bit 0 of LUT
    pqsc.feedback.decoder.lut.sources[0].index(
        INT_UNIT
    )  # Source bit in READOUT_REGISTER for bit 0 of LUT
    lut = np.array([1, 0], dtype=np.uint32)  # LUT[0] -> 1 and LUT[1] -> 0
    pqsc.feedback.decoder.lut.tables[0](lut)
```

Finally, enable the Decoder.

```python
# Find SHFSG and SHFQA ZSync port IDs
shfsg_zsync_port = pqsc.find_zsync_worker_port(shfsg)
shfqa_zsync_port = pqsc.find_zsync_worker_port(shfqa)

with session.set_transaction():
    # Enable Decoder Unit
    for zsync_port in [shfsg_zsync_port, shfqa_zsync_port]:
        pqsc.zsyncs[zsync_port].output.source("decoder")  # Enable Decoder
        pqsc.zsyncs[zsync_port].output.enable(True)       # Enable ZSync feedback
        pqsc.zsyncs[zsync_port].output.decoder.source(0)  # Index of LUT being forwarded
```

## SHFSG sequencer program

The only part still missing is the configuration of the SHFSG. In the following sequencer program we tell the SHFSG to:
1. Play a "try" waveform at the beginning of each iteration
2. Stay silent for `section_len`, previously calculated such that `section_len + WAVEFORM_TRY_LEN` corresponds to an integer multiple of 200 ns;
3. Acquire the feedback value sent by the PQSC over ZSync, waiting a time `feedback_time` with respect to the initial start trigger;
4. Update the feedback time for the next ieration.

We repeat these steps as long as the the feedback value received by the PQSC (which we call `failure`) is 1. When `failure` is 0 the while loop ends and the SHFSG will play a "success" pulse, with half the amplitude and double the duration with respect to the "try" waveform.

```python
seqc_program_shfsg = tk.Sequence()

constants = {
    "feedback_latency": feedback_latency,
    "cycle_len_clocks": cycle_len_clocks,
    "WAVEFORM_TRY_LEN": WAVEFORM_TRY_LEN,
    "section_len": section_len,
}
seqc_program_shfsg.constants = constants

seqc_program_shfsg.waveforms = tk.Waveforms()
seqc_program_shfsg.waveforms[0] = tk.waveform.Wave(1.0 * np.ones(WAVEFORM_TRY_LEN), name="w_try")
seqc_program_shfsg.waveforms[1] = tk.waveform.Wave(
    0.5 * np.ones(WAVEFORM_TRY_LEN * 2), name="w_success"
)

seqc_program_shfsg.code = textwrap.dedent(
    """\
    var failure;
    var feedback_time = feedback_latency;

    var cnt_failures = 0;                                                   // Counter for number of failures
    var cnt_try = 0;                                                        // Counter for total number of "try"

    waitZSyncTrigger();

    do {
        playWave(w_try);                                                    // Play "try" pulse
        playZero(section_len);                                              // Define next section length
    
        failure = getFeedback(ZSYNC_DATA_PQSC_DECODER, feedback_time);      // Acquire feedback value from PQSC
        feedback_time += cycle_len_clocks;                              // Update feedback latency for following cycle

        cnt_failures += failure;                                            // Update counters
        cnt_try += 1;
    } while (failure);

    // Success pulse
    playWave(w_success);

    setUserReg(0, cnt_failures);                                            // Save counters to user register to check them later
    setUserReg(1, cnt_try);
"""
)
shfsg.sgchannels[SG_CHANNEL].awg.load_sequencer_program(seqc_program_shfsg)
shfsg.sgchannels[SG_CHANNEL].awg.write_to_waveform_memory(seqc_program_shfsg.waveforms)
```

The PQSC sends up to four qubit states at the same time. Configure the SHFSG to look only at the one interesting for us, i.e. the least significant one. The data is processed by the sequencer according to the following formula:

```
feedback_data = ((zsync_raw_message >> shift) & mask) + offset
```

so to look at the least significant bit, we need to shift by zero positions, mask the last bit (mask = 0b0001) and add no offset.

```python
with session.set_transaction():
    shfsg.sgchannels[SG_CHANNEL].awg.zsync.decoder.shift(0)
    shfsg.sgchannels[SG_CHANNEL].awg.zsync.decoder.mask(0b1)
    shfsg.sgchannels[SG_CHANNEL].awg.zsync.decoder.offset(0)
```

## Run the experiment


We can finally put all the pieces together and run the experiment: enable the readout, the SHFSG awg sequencer, the SHFQA readout pulse generator and finally send the start triggers with the PQSC.

```python
import rtlogger_helpers

with session.set_transaction():
    # Reset RT Logger
    rtlogger_helpers.reset_and_enable_rtlogger(
        shfsg.sgchannels[SG_CHANNEL].awg
    )
    # Prepare the PQSC for triggering
    pqsc.arm(repetitions=1, holdoff=100e-3)
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
```

To check that everything was correct we print the values of `cnt_failures` and `cnt_try` previously saved in the SHFSG user register. We also print the data collected by the RT Logger, which is a tool for logging data received over ZSync. Data with timestamp 0 correspond to start trigger events; the column "decoder data" shows the data coming from the Decoder Unit of the PQSC.

```python
print(
    "Accumulated data: ",
    shfsg.sgchannels[SG_CHANNEL].awg.userregs[0](deep=True)[1],
    " - Expected accumulated data: ",
    SIMULATED_FAILURES,
)
print(
    "Counter executions: ",
    shfsg.sgchannels[SG_CHANNEL].awg.userregs[1](deep=True)[1],
    " - Expected counter executions: ",
    SIMULATED_FAILURES + 1,
)
```

```python
rtlogger_helpers.print_rtlogger_data(session, shfsg.sgchannels[SG_CHANNEL].awg)
```
