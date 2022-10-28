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

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### Instrument configuration

```python
OUT_CHANNEL = 0
OUT_MIXER_CHANNEL = 1 # UHFLI: 3, HF2LI: 6, MFLI: 1
IN_CHANNEL = 0
DEMOD_INDEX = 0
OSC_INDEX = 0

with device.set_transaction():
    device.sigins[IN_CHANNEL].ac(0)
    device.sigins[IN_CHANNEL].range(0.2)

    device.demods[DEMOD_INDEX].enable(True)
    device.demods[DEMOD_INDEX].rate(10e3)
    device.demods[DEMOD_INDEX].adcselect(IN_CHANNEL)
    device.demods[DEMOD_INDEX].order(4)
    device.demods[DEMOD_INDEX].timeconstant(0.01)
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
sweeper.stop(500e3) # 500e3 for MF devices, 50e6 for others
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

Note, this is not the subscribe from ziDAQServer; it is a Module subscribe.
The Sweeper Module needs to subscribe to the nodes it will return data for.

```python
sample_node = device.demods[DEMOD_INDEX].sample
sweeper.subscribe(sample_node)
```

### Configuring the data saving settings


Query available file format options

```python
sweeper.save.fileformat.node_info.options
```

Set the filename stem for saving the data to file. The data are saved in a separate
numerically incrementing sub-directory prefixed with the `/save/filename` value each
time a save command is issued. The base directory is specified with the
`save/directory` parameter. 

```python
sweeper.save.filename('sweep_with_save')
sweeper.save.fileformat('hdf5')
```

### Executing the sweeper

Setup logging to see the progress of the `wait_done` function.

```python
import logging
import sys

handler = logging.StreamHandler(sys.stdout)
logging.getLogger("zhinst.toolkit").setLevel(logging.INFO)
logging.getLogger("zhinst.toolkit").addHandler(handler)
```

```python
sweeper.execute()
print(f"Perform {LOOPCOUNT} sweeps")
sweeper.wait_done(timeout=300)
```

Instead of waiting for the the sweeper to finish before reading/saving the data, one can 
also read the data continuously through the `sweeper.read()` function.


### Saving the data

Indicate that the data should be saved to file. This must be done before the read()
command. Otherwise there is no longer any data to save.

```python
sweeper.save.save(True)
# Wait until the save is complete. The saving is done asynchronously in the background
# so we need to wait until it is complete. In the case of the sweeper it is important
# to wait for completion before before performing the module read command. The sweeper has
# a special fast read command which could otherwise be executed before the saving has
# started.
sweeper.save.save.wait_for_state_change(True, invert=True, timeout=5)
```

### Reading the data from the module

Read the data and unsubscribe from the selected node.

The read command can also be executed whilst sweeping (before finished() is True),
in this case sweep data up to that time point is returned. It's still necessary
to issue read() at the end to fetch the remaining data.

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
ax1.set_title(f"Results of {len(node_samples)} sweeps.")
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
