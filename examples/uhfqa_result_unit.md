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

# Result Unit

This example demonstrates how to use the result unit for acquiring data
after weighted integration, rotation, and crosstalk suppression.

A single non-zero coefficient in each weighting function is activated. As a
consequence, the result unit will sample just a single input sample each
time it is started. We then configure the AWG to output a bipolar square
wave. The AWG plays the waveform in a loop for each measurement and all
averages. The AWG sweeps the starting point of the integration for each
measurement. The final result is that we record essentially the input
waveform using the result unit. The step size corresponds to the wait time
in the AWG, which is 4.44 ns. Finally, we configure a different coefficient
for each of the 10 input channels to enable the user to differentiate the
channels in the plot output.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x UHFQA instrument.
* Signal output 1 connected to signal input 1 with a BNC cable.
* Signal output 2 connected to signal input 2 with a BNC cable.


```python
import numpy as np
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### Initialize the device

```python
with device.set_transaction():
    device.sigins['*'].range(1.5)
    device.sigouts['*'].range(1.5)

    device.sigins['*'].imp50(1)
    device.sigouts['*'].imp50(1)
    device.sigouts['*'].on(True)

    device.awgs['*'].outputs['*'].mode(0)

    device.dios[0].mode(2)
    device.dios[0].drive(2)

    device.qas[0].delay(0)
    device.qas[0].deskew.rows[0].cols[0](1)
    device.qas[0].deskew.rows[0].cols[1](0)
    device.qas[0].deskew.rows[1].cols[0](0)
    device.qas[0].deskew.rows[1].cols[1](1)
    device.qas[0].result.length(1.0)
    device.qas[0].result.averages(0)
    device.qas[0].result.source(0) # Trans
    device.qas[0].result.statistics.length(1.0)
    device.qas[0].monitor.length(1024)
```

### Configure rotation, transformation, threshold and integration weights

```python
N_READOUT_CHANNELS = 10
```

```python
with device.set_transaction():
    for i in range(N_READOUT_CHANNELS):
        device.qas[0].rotations[i](1 + 0j)
        device.qas[0].thresholds[i].level(1.0)

        device.qas[0].integration.weights[i].real(np.zeros(4096))
        device.qas[0].integration.weights[i].imag(np.zeros(4096))
    device.qas[0].integration.length(1)
    device.qas[0].crosstalk_matrix(np.identity(N_READOUT_CHANNELS, dtype=int))

```

### Configure AWG sequence program

```python
awg_program = """\
wave w = join(zeros(64), ones(10000), -ones(10000));
var loop_cnt = getUserReg(0);
var avg_cnt = getUserReg(1);
var wait_delta = 1;

repeat (avg_cnt) {
    var wait_time = 0;

    repeat(loop_cnt) {
        wait_time += wait_delta;
        playWave(w, w);
        wait(wait_time);
        startQA(QA_INT_0 | QA_INT_1, true);
        playZero(8*1024);
    }
}
"""
```

```python
device.awgs[0].load_sequencer_program(awg_program)
```

Apply a rotation on half the channels to get the imaginary part instead

```python
for i in range(5):
    device.qas[0].rotations[i](1)
    device.qas[0].rotations[i+5](-1j)
```

Channels to test

```python
CHANNELS = np.arange(0, N_READOUT_CHANNELS, 1)
RESULT_LENGTH = 2600
NUM_AVERAGES = 1
```

Configuration of weighted integration

```python
weights = np.linspace(1.0, 0.1, N_READOUT_CHANNELS)

for i in CHANNELS:
    weight = np.array([weights[i]])
    device.qas[0].integration.weights[i].real(weight)
    device.qas[0].integration.weights[i].imag(weight)

device.qas[0].integration.length(1)
device.qas[0].integration.mode(0)
device.qas[0].delay(0)

device.awgs[0].userregs[0](RESULT_LENGTH)
device.awgs[0].userregs[1](NUM_AVERAGES)
```

Configure and enable the result unit

```python
with device.set_transaction():
    device.qas[0].result.length(RESULT_LENGTH)
    device.qas[0].result.averages(NUM_AVERAGES)
    device.qas[0].result.source(0) # Trans
    device.qas[0].result.reset(True)
    device.qas[0].result.enable(True)
```

### Subscribing to nodes

```python
# In order to keep track of which nodes we want to capture
# we create a dictionary
wave_data_captured = {}

for ch in CHANNELS:
    node = device.qas[0].result.data[ch].wave
    node.subscribe()
    wave_data_captured[str(node)] = False
```

Arm the device

```python
device.awgs[0].single(True)
device.awgs[0].enable(True, deep=True)
```

### Capture data

Poll the data until the selected number of samples is captured.

```python
import time
import copy
from zhinst.toolkit.nodetree.helper import NodeDict

timeout = RESULT_LENGTH / 150  # Rough estimate to prevent endless loop
start_time = time.time()

captured_data = {}

while not all(wave_data_captured.values()):
    if start_time + timeout < time.time():
        raise TimeoutError('Timeout before all samples collected.')
    for node, value in session.poll().items():
        if node not in captured_data:
            captured_data[node] = value[0]['vector']
        else:
            captured_data[node].append(value[0]['vector'])
        if len(captured_data[node]) >= RESULT_LENGTH:
            wave_data_captured[node] = True
```

Stop the result unit

```python
device.qas[0].result.data.unsubscribe()
device.qas[0].result.enable(False)
```

### Plot the results

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(figsize=(12, 4))

axes.set_title("Result unit")
axes.set_ylabel("Amplitude (a.u.)")
axes.set_xlabel("Measurement (#)")
for path, samples in captured_data.items():
    axes.plot(samples, label=f"{path}")
plt.legend(loc="best", fontsize=6)
fig.set_tight_layout(True)
plt.grid()
plt.show()
```
