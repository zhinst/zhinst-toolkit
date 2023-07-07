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

# SHFQA Sweeper

This example shows how to perform resonator spectroscopy using the sweeper functionality of the SHFQA.

Requirements:

* LabOne >= 22.02
* Instruments:
    1 x SHFQA

Create a toolkit session to the data server and connect the device:

```python
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
sweeper = session.modules.shfqa_sweeper
CHANNEL = 0
```

For now the general sweeper module does not support the SHFQA. However a
python-based implementation called ``SHFSweeper`` does already provide
this functionality. The ``SHFSweeper`` is part of the ``zhinst`` module
and can be found in the utils.

Toolkit wraps around the ``SHFSweeper`` and exposes an interface that is
similar to the LabOne modules, meaning the parameters are exposed in a
node tree like structure.

All parameters can be accessed through their corresponding node:

* device: Device to run the sweeper with
* sweep: Frequency range settings for a sweep
* rf: RF in- and output settings for a sweep
* average: Averaging settings for a sweep
* trigger: Settings for the trigger
* envelope: Settings for defining a complex envelope for pulsed spectroscopy

The underlying module is updated with the parameter changes automatically.
Every functions from the underlying SHFSweeper module is exposed and can be
used in the same way.

In this example we show how to perform continuous and pulsed resonator spectroscopy in toolkit with the sweeper module.

## Continuous resonator spectroscopy
In continuous spectroscopy the resonator is probed with a continuous wave. 
### Configure the sweeper
Configure the sequencer by specifying the frequencies to be swept, the averaging settings and the input and output ranges.
Moreover, the toolkit sweeper module requires to specify the device it will use as well.

```python
sweeper.device(device)

sweeper.sweep.start_freq(200e6)
sweeper.sweep.stop_freq(300e6)
sweeper.sweep.num_points(501)
sweeper.sweep.oscillator_gain(0.7)
# The sequencer is used by default but can be disabled manually
# sweeper.sweep.mode("host-driven")
sweeper.sweep.mode("sequencer-based")

# NOTE: we recommend users to disable the Scope in the GUI when the 
# sweeper is running to avoid potential timeout errors. Alternatively,
# an additional wait time after integration can be added with the following
# command, in case the Scope needs to be running during the sweep: 
# sweeper.sweep.wait_after_integration(4e-6)

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

## Pulsed resonator spectroscopy
In pulsed spectroscopy the resonator is probed with a signal consisting of an envelope modulated at some frequency. In toolkit we only need to specify the envelope of the pulse, and the modulation is performed by the sweeper module automatically.
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

### Plot Envelope

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
sweeper.sweep.oscillator_gain(0.7)
sweeper.sweep.use_sequencer=True

sweeper.average.integration_time(envelope_duration)
sweeper.average.num_averages(2)
sweeper.average.mode("sequential")

# Note: the default integration delay amounts to 224 ns to compensate the device-
# internal delay from output to input.
# You can set a different integration delay, for example to compensate additional
# delays in the device under test by using the following line:
# sweeper.average.integration_delay(224.0e-9)

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