---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.13.7
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# SHFQA Sweeper

Requirements:

* LabOne >= 22.02
* Instruments:
    1 x SHFQA

Create a toolkit session to the data server and connect the device:

```python
from zhinst.toolkit import Session

session = Session('localhost')
device = session.connect_device("DEVXXXX")
sweeper = session.modules.shfqa_sweeper
CHANNEL = 0
```

For now the general sweeper module does not support the SHFQA. However a
python based implementation called ``SHFSweeper`` does already provide
this functionality. The ``SHFSweeper`` is part of the ``zhinst`` module
and can be found in the utils.

Toolkit wraps around the ``SHFSweeper`` and exposes a interface that is
similar to the LabOne modules, meaning the parameters are exposed in a
node tree like structure.

All parameters can be accessed through their corresponding node:

* device: Device to run the sweeper with
* sweep: Frequency range settings for a sweep
* rf: RF in- and ouput settings for a sweep
* average: Averaging settings for a sweep
* trigger: Settings for the trigger
* envelope: Settings for defining a complex envelope for pulsed spectroscopy

The underlying module is updated with the parameter changes automatically.
Every functions from the underlying SHFSweeper module is exposed and can be
used in the same way.


## Run a frequency sweep
### Configure the sweeper

(Besides the measurement specific parameters the device that the sweeper will use
must be specfied as well.)

```python
sweeper.device(device)

sweeper.sweep.start_freq(200e6)
sweeper.sweep.stop_freq(300e6)
sweeper.sweep.num_points(501)
sweeper.sweep.oscillator_gain(0.8)
# The sequencer is used by default but can be disabled manually
# (sequencer-based sweep (True) or the slower host-driven sweep (False))
sweeper.sweep.use_sequencer=True

sweeper.average.integration_time(100e-6)
sweeper.average.num_averages(200)
sweeper.average.mode("sequential")


sweeper.rf.channel(CHANNEL)
sweeper.rf.input_range(0)
sweeper.rf.output_range(0)
sweeper.rf.center_freq(4e9)
```

### Turn on the input / output channel

```python
with device.set_transaction():
    device.qachannels[CHANNEL].input.on(1)
    device.qachannels[CHANNEL].output.on(1)
```

### Execute the sweeper

```python
result = sweeper.run()
num_points_result = len(result["vector"])
print(f"Measured at {num_points_result} frequency points.")
```

```python
sweeper.plot()
```

## Pulsed resonator with complex envelope

### Create the envelope

```python
from scipy.signal import gaussian
import numpy as np

SHFQA_SAMPLING_FREQUENCY = 2e9
envelope_duration = 1.0e-6
envelope_rise_fall_time = 0.05e-6

rise_fall_len = int(envelope_rise_fall_time * SHFQA_SAMPLING_FREQUENCY)
std_dev = rise_fall_len // 10
gauss = gaussian(2 * rise_fall_len, std_dev)
flat_top_gaussian = np.ones(int(envelope_duration * SHFQA_SAMPLING_FREQUENCY))
flat_top_gaussian[0:rise_fall_len] = gauss[0:rise_fall_len]
flat_top_gaussian[-rise_fall_len:] = gauss[-rise_fall_len:]
```

#### Plot Envelope

```python
import matplotlib.pyplot as plt
plt.plot(flat_top_gaussian)
plt.show()
```

### Configure the sweeper

```python
sweeper.device(device)

sweeper.sweep.start_freq(-200e6)
sweeper.sweep.stop_freq(300e6)
sweeper.sweep.num_points(51)
sweeper.sweep.oscillator_gain(0.8)
sweeper.sweep.use_sequencer=False

sweeper.average.integration_time(envelope_duration)
sweeper.average.num_averages(2)
sweeper.average.mode("sequential")
sweeper.average.integration_delay(0.0)

sweeper.rf.channel(CHANNEL)
sweeper.rf.input_range(0)
sweeper.rf.output_range(0)
sweeper.rf.center_freq(4e9)

sweeper.envelope.enable(True)
sweeper.envelope.waveform(flat_top_gaussian)
sweeper.envelope.delay(0.0)
```

### Turn on the input / output channel

```python
with device.set_transaction():
    device.qachannels[CHANNEL].input.on(1)
    device.qachannels[CHANNEL].output.on(1)
```

### Execute the sweeper

```python
result = sweeper.run()
num_points_result = len(result["vector"])
print(f"Measured at {num_points_result} frequency points.")
```

```python
sweeper.plot()
```

```python

```
