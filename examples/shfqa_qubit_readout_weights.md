---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.14.1
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# Measuring qubit readout weights

This example shows how to use the SHFQA to measure the integration weights needed for a high-fidelity single-shot qubit readout.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x SHFQA Instrument
* Loopback configuration between input and output of channel 0

```python
from zhinst.toolkit import Session, SHFQAChannelMode, Waveforms

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### Configure channel inputs and outputs
Set the center frequency for the signals, the input and output range (in dB) and the mode of the SHFQA channel.
```python
CHANNEL_INDEX = 0

device.qachannels[CHANNEL_INDEX].configure_channel(
    center_frequency=5e9,
    input_range=0,
    output_range=-5,
    mode=SHFQAChannelMode.READOUT,
)
device.qachannels[CHANNEL_INDEX].input.on(1)
device.qachannels[CHANNEL_INDEX].output.on(1)
```

### Configure scope
In this example the scope is used to detect the response of the qubit to the readout pulses, from which it is possible to calculate the optimal integration weights. Here we configure the scope parameters in order to record 2 segments of data, corresponding to the qubit being in the ground and excited state, which are averaged 50 times.

```python
SCOPE_CHANNEL = 0
NUM_QUBITS = device.max_qubits_per_channel
READOUT_DURATION = 600e-9
NUM_SEGMENTS = 2
NUM_AVERAGES = 50
NUM_MEASUREMENTS = NUM_SEGMENTS * NUM_AVERAGES
SHFQA_SAMPLING_FREQUENCY = 2e9

device.scopes[SCOPE_CHANNEL].configure(
    input_select={SCOPE_CHANNEL: f"channel{CHANNEL_INDEX}_signal_input"},
    num_samples=int(READOUT_DURATION * SHFQA_SAMPLING_FREQUENCY),
    trigger_input=f"channel{CHANNEL_INDEX}_sequencer_monitor0",
    num_segments=NUM_SEGMENTS,
    num_averages=NUM_AVERAGES,
    trigger_delay=200e-9,
)
```

### Generate waveforms
Generate the readout pulses with a flat top gaussian envelope. For each qubit the generator sends the pulses to readout the state of the qubit, which is prepared in the ground and excited state; the scope then acquires the response signal of the qubit and the integration weights are calculated.

```python

from scipy.signal import gaussian
import numpy as np

# Define the parameters for the readout pulses
RISE_FALL_TIME = 10e-9
PULSE_DURATION = 500e-9
FREQUENCIES = np.linspace(2e6, 32e6, NUM_QUBITS)  # Qubits' frequencies

rise_fall_len = int(RISE_FALL_TIME * SHFQA_SAMPLING_FREQUENCY)
pulse_len = int(PULSE_DURATION * SHFQA_SAMPLING_FREQUENCY)
std_dev = rise_fall_len // 10

# Generate the flat top gaussian envelope
gauss = gaussian(2 * rise_fall_len, std_dev)
flat_top_gaussian = np.ones(pulse_len)
flat_top_gaussian[0:rise_fall_len] = gauss[0:rise_fall_len]
flat_top_gaussian[-rise_fall_len:] = gauss[-rise_fall_len:]
# Scaling
flat_top_gaussian *= 0.9

readout_pulses = Waveforms()
time_vec = np.linspace(0, PULSE_DURATION, pulse_len)

# Modulate the envelope at the qubits' frequencies
for i, f in enumerate(FREQUENCIES):
    readout_pulses.assign_waveform(
        slot=i,
        wave1=flat_top_gaussian * np.exp(2j * np.pi * f * time_vec)
    )

device.qachannels[CHANNEL_INDEX].generator.write_to_waveform_memory(readout_pulses)
```

### Configure sequencer
Configure the sequencer triggering.
```python
device.qachannels[CHANNEL_INDEX].generator.configure_sequencer_triggering(
    aux_trigger="software_trigger0",
    play_pulse_delay=0
)
```

### Run the measurement and calculate the integration weights
The integration weights are measured sequentially for different qubits. For each qubit the generator sends the pulses to readout the qubit prepared in the ground and the excited state, the scope acquires the response signal of the qubit and the integration weights are calculated.
```python
results = []

for i in range(NUM_QUBITS):
    qubit_result = {
        'weights': None,
        'ground_states': None,
        'excited_states': None
    }
    print(f"Measuring qubit {i}.")

    # Upload sequencer program
    seqc_program = f"""
        repeat({NUM_MEASUREMENTS}) {{
            waitDigTrigger(1);
            startQA(QA_GEN_{i}, 0x0, true,  0, 0x0);
        }}
    """
    device.qachannels[CHANNEL_INDEX].generator.load_sequencer_program(seqc_program)

    # Start a measurement
    device.scopes[SCOPE_CHANNEL].run(single=True)
    device.qachannels[CHANNEL_INDEX].generator.enable_sequencer(single=True)
    device.start_continuous_sw_trigger(
        num_triggers=NUM_MEASUREMENTS, wait_time=READOUT_DURATION
    )

    # Get results to calculate weights and plot data
    scope_data, *_ = device.scopes[0].read()

    # Calculates the weights from scope measurements
    # for the excited and ground states
    split_data = np.split(scope_data[SCOPE_CHANNEL], 2)
    ground_state_data = split_data[0]
    excited_state_data = split_data[1]
    qubit_result['ground_state_data'] = ground_state_data
    qubit_result['excited_state_data'] = excited_state_data
    qubit_result['weights'] = np.conj(excited_state_data - ground_state_data)
    results.append(qubit_result)
```

### Plot results
Plot the response signals of the qubit and the calculated integration weights.
```python
import matplotlib.pyplot as plt

QUBIT = 0

qubit_result = results[QUBIT]
ground_state_data = qubit_result['ground_state_data']
excited_state_data = qubit_result['excited_state_data']
weights = qubit_result['weights']

# Plot the data
# Plot the data measured with the scope for weight calculation
time_ticks = np.array(range(len(ground_state_data))) / SHFQA_SAMPLING_FREQUENCY

fig = plt.figure(1)
fig.suptitle("Scope measurement for readout weights")

ax1 = plt.subplot(211)
ax1.plot(time_ticks, np.real(ground_state_data))
ax1.plot(time_ticks, np.imag(ground_state_data))
ax1.set_title("ground state")
ax1.set_ylabel("voltage [V]")
plt.setp(ax1.get_xticklabels(), visible=False)
ax1.xaxis.get_offset_text().set_visible(False)
ax1.grid()
plt.legend(["real", "imag"])

ax2 = plt.subplot(212, sharex=ax1)
ax2.plot(time_ticks, np.real(excited_state_data))
ax2.plot(time_ticks, np.imag(excited_state_data))
ax2.set_title("excited state")
ax2.set_xlabel("t [s]")
ax2.set_ylabel("voltage [V]")
ax2.grid()
plt.show()

# Plot the qubit readout weights
time_ticks = np.array(range(len(weights))) / SHFQA_SAMPLING_FREQUENCY
plt.plot(time_ticks, np.real(weights))
plt.plot(time_ticks, np.imag(weights))
plt.title("Qubit readout weights")
plt.xlabel("t [s]")
plt.ylabel("weights [V]")
plt.legend(["real", "imag"])
plt.grid()
plt.show()
```
