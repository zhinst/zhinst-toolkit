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

# Qubit readout measurements

This examples shows how to perform the multiplexed readout of multiple qubits using the SHFQA.

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

### Generate the waveforms to readout the state of the qubits.
In this example the envelope of the readout pulses is a gaussian with a flat top. For each qubit, the envelope is then modulated at the qubit frequency. For illustrative purposes we assume that the frequencies of the qubits are equally spaced in the range [32 MHz, 230 MHz] relative to the center frequency of 5 GHz specified above.

```python
from scipy.signal import gaussian
import numpy as np

# Define the parameters for the readout pulses
NUM_QUBITS = device.max_qubits_per_channel
RISE_FALL_TIME = 10e-9  # Duration of the rising and falling parts of the pulse
SAMPLING_RATE = 2e9
PULSE_DURATION = 500e-9  # Total pulse duration
FREQUENCIES = np.linspace(32e6, 230e6, NUM_QUBITS)  # Qubits' frequencies
SCALING = 0.9 / NUM_QUBITS

rise_fall_len = int(RISE_FALL_TIME * SAMPLING_RATE)
pulse_len = int(PULSE_DURATION * SAMPLING_RATE)
std_dev = rise_fall_len // 10

# Generate the flat top gaussian envelope
gauss = gaussian(2 * rise_fall_len, std_dev)
flat_top_gaussian = np.ones(pulse_len)
flat_top_gaussian[0:rise_fall_len] = gauss[0:rise_fall_len]
flat_top_gaussian[-rise_fall_len:] = gauss[-rise_fall_len:]
# Scaling
flat_top_gaussian *= SCALING

time_vec = np.linspace(0, PULSE_DURATION, pulse_len)

# Modulate the envelope at the qubits' frequencies
readout_pulses = Waveforms()
for i, f in enumerate(FREQUENCIES):
    readout_pulses.assign_waveform(
        slot=i,
        wave1=flat_top_gaussian * np.exp(2j * np.pi * f * time_vec)
    )

# Upload the waveforms to the waveform memory
device.qachannels[CHANNEL_INDEX].generator.write_to_waveform_memory(readout_pulses)
```

### Configure result logger and weighted integration
Configure the weights to be used in the weighted integration for the readout of the qubits. We also configure the result logger, specifying the number of readouts to be performed.

```python
ROTATION_ANGLE = 0
NUM_READOUTS = 100

# Define the weights for the weighted integration
weights =  Waveforms()

for waveform_slot, pulse in readout_pulses.items():
    weights.assign_waveform(
        slot=waveform_slot,
        wave1=np.conj(pulse[0] * np.exp(1j * ROTATION_ANGLE))
    )

device.qachannels[CHANNEL_INDEX].readout.write_integration_weights(
    weights=weights,
    # compensation for the delay between generator output and input of the integration unit
    integration_delay=200e-9
)

# Configure the result logger
device.qachannels[CHANNEL_INDEX].readout.configure_result_logger(
    result_length=NUM_READOUTS,
    result_source='result_of_integration'
)
```

### Configure sequencer
Configure the sequencer to wait for the triggering signal, start the readout, and then repeat this procedure for the chosen number of readouts. We also configure the type of trigger to be used.

```python
device.qachannels[CHANNEL_INDEX].generator.configure_sequencer_triggering(
    aux_trigger="software_trigger0",
    play_pulse_delay=0
)
```

```python
seqc_program = f"""
    repeat({NUM_READOUTS}) {{
        waitDigTrigger(1);
        startQA(QA_GEN_ALL, QA_INT_ALL, true, 0, 0x0);
    }}
"""
device.qachannels[CHANNEL_INDEX].generator.load_sequencer_program(seqc_program)
```

### Run experiment

```python
device.qachannels[CHANNEL_INDEX].readout.run()
device.qachannels[CHANNEL_INDEX].generator.enable_sequencer(single=True)
device.start_continuous_sw_trigger(
    num_triggers=NUM_READOUTS, wait_time=2e-3
)
```

### Get results

```python
readout_results = device.qachannels[CHANNEL_INDEX].readout.read()
```

Plot results

```python
import matplotlib.pyplot as plt

max_value = 0
readout_results = readout_results[:NUM_QUBITS]
plt.rcParams["figure.figsize"] = [10, 10]

for complex_number in readout_results:
    real = np.real(complex_number)
    imag = np.imag(complex_number)

    plt.plot(real, imag, "x")

    max_value = max(max_value, max(abs(real)))
    max_value = max(max_value, max(abs(imag)))

# zoom so that the origin is in the middle
max_value *= 1.05
plt.xlim([-max_value, max_value])
plt.ylim([-max_value, max_value])

plt.legend(range(len(readout_results)))
plt.title("qubit readout results")
plt.xlabel("real part")
plt.ylabel("imaginary part")
plt.grid()
plt.show()
```
