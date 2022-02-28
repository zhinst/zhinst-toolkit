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

# Sweeper

Demonstrate how to perform a simple frequency sweep using the Sweeper module.
Perform a frequency sweep and record demodulator data.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x Instrument with demodulators
* feedback cable between Signal Output 1 and Signal Input 1

```python
from zhinst.toolkit import Session

session = Session('localhost')
device = session.connect_device("DEVXXXX")
```

```python
OUT_CHANNEL = 0
# UHFLI: 3, HF2LI: 6, MFLI: 1
OUT_MIXER_CHANNEL = 1
IN_CHANNEL = 0
DEMOD_INDEX = 0
OSC_INDEX = 0
DEMOD_RATE = 10e3
TIME_CONSTANT = 0.01
AMPLITUDE = 0.2
```

### Instrument configuration

```python
with device.set_transaction():
    device.sigins[IN_CHANNEL].ac(0)
    device.sigins[IN_CHANNEL].range(AMPLITUDE)

    device.demods[DEMOD_INDEX].enable(True)
    device.demods[DEMOD_INDEX].rate(DEMOD_RATE)
    device.demods[DEMOD_INDEX].adcselect(IN_CHANNEL)
    device.demods[DEMOD_INDEX].order(4)
    device.demods[DEMOD_INDEX].timeconstant(TIME_CONSTANT)
    device.demods[DEMOD_INDEX].oscselect(OSC_INDEX)
    device.demods[DEMOD_INDEX].harmonic(1)

    device.sigouts[OUT_CHANNEL].on(True)
    device.sigouts[OUT_CHANNEL].enables[OUT_MIXER_CHANNEL](1)
    device.sigouts[OUT_CHANNEL].range(1)
    device.sigouts[OUT_CHANNEL].amplitudes(OUT_MIXER_CHANNEL)
```

### Configuring the Sweep module

```python
# Specify the number of sweeps to perform back-to-back.
LOOPCOUNT = 2

sweeper = session.modules.sweeper
sweeper.device(device)

sweeper.gridnode(device.oscs[OSC_INDEX].freq)
sweeper.start(4e3)
# 500e3 for MF devices, 50e6 for others
sweeper.stop(500e3)
sweeper.samplecount(100)
sweeper.xmapping(1)
sweeper.bandwidthcontrol(2)
sweeper.bandwidthoverlap(0)
sweeper.scan(0)
sweeper.loopcount(LOOPCOUNT)
sweeper.settling.time(0)
sweeper.settling.inaccuracy(0.001)
sweeper.averaging.tc(10)
sweeper.averaging.sample(10)
```

### Subscribing to a sample node

```python
sample_node = device.demods[DEMOD_INDEX].sample
sweeper.subscribe(sample_node)
```

### Configuring the data saving settings


Query available file format options

```python
sweeper.save.fileformat.node_info.options
```

```python
sweeper.save.filename('sweep_with_save')
sweeper.save.fileformat('hdf5')
```

### Executing the sweeper

```python
sweeper.execute()
sweeper.wait_done(timeout=300)
```

### Saving the data

```python
sweeper.save.save(True)
sweeper.save.save.wait_for_state_change(True, invert=True, timeout=5)
```

### Reading the data from the module

Read the data and unsubscribe from the selected node.

```python
data = sweeper.read()
sweeper.unsubscribe(sample_node)
```

Verify that the number of sweeps is correct.

```python
num_sweeps = len(data[sample_node])
assert num_sweeps == LOOPCOUNT, (
    f"The sweeper returned an unexpected number of sweeps: "
    f"{num_sweeps}. Expected: {LOOPCOUNT}."
)
```

### Plot the data

```python
import matplotlib.pyplot as plt
import numpy as np

node_samples = data[sample_node]

_, (ax1, ax2) = plt.subplots(2, 1)
for sample in node_samples:
    frequency = sample[0]["frequency"]
    demod_r = np.abs(sample[0]["x"] + 1j * sample[0]["y"])
    phi = np.angle(sample[0]["x"] + 1j * sample[0]["y"])
    ax1.plot(frequency, demod_r)
    ax2.plot(frequency, phi)
ax1.set_title("Results of %d sweeps." % len(node_samples))
ax1.grid()
ax1.set_ylabel(r"Demodulator R ($V_\mathrm{RMS}$)")
ax1.set_xscale("log")
ax2.autoscale()

ax2.grid()
ax2.set_xlabel("Frequency ($Hz$)")
ax2.set_ylabel(r"Demodulator Phi (radians)")
ax2.set_xscale("log")
ax2.autoscale()

plt.draw()
plt.show()
```
