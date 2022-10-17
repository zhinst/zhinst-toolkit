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

# DAQ Data Acquisition

Example for the Data Acquisition Module. This example demonstrates
how to record data from an instrument continuously (without triggering).
Record data continuously in 0.2 s chunks for 5 seconds by using the Data Acquisition Module.

Note:
This example does not perform any device configuration. If the streaming
nodes corresponding to the signal paths are not enabled, no data will be
recorded.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x Instrument with demodulators
* A feedback cable between Signal Output 1 and Signal Input 1

```python
from zhinst.toolkit import Session
import numpy as np

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### General configuration


#### Selecting the signal paths for recording

```python
device.demods[0].enable(True)

sample_nodes = [
    device.demods[0].sample.x,
    device.demods[0].sample.y
]
```

### Create and configure the Data Acquisition module


#### General parameters

```python
TOTAL_DURATION = 5 # [s]
SAMPLING_RATE = 30000 # Number of points/second
BURST_DURATION = 0.2 # Time in seconds for each data burst/segment.

num_cols = int(np.ceil(SAMPLING_RATE * BURST_DURATION))
num_bursts = int(np.ceil(TOTAL_DURATION / BURST_DURATION))
```

#### Module creation

```python
daq_module = session.modules.daq
daq_module.device(device)
daq_module.type(0) # continuous acquisition
daq_module.grid.mode(2)
daq_module.count(num_bursts)
daq_module.duration(BURST_DURATION)
daq_module.grid.cols(num_cols)
```

#### Configuring the data saving settings

```python
daq_module.save.fileformat(1)
daq_module.save.filename('zi_toolkit_acq_example')
daq_module.save.saveonread(1)
```

#### Subscribing to the nodes

```python
for node in sample_nodes:
    daq_module.subscribe(node)
```

```python
clockbase = device.clockbase()
```

### Recording and plotting the data


Helper function for reading and plotting the data

```python
import matplotlib.pyplot as plt
%matplotlib notebook
```

```python
def read_and_plot_data(daq_module, results, ts0):
    daq_data = daq_module.read(raw=False, clk_rate=clockbase)
    progress = daq_module.raw_module.progress()[0]
    for node in sample_nodes:
        # Check if node data available
        if node in daq_data.keys():
            for sig_burst in daq_data[node]:
                results[node].append(sig_burst)
                if np.any(np.isnan(ts0)):
                  ts0 = sig_burst.header['createdtimestamp'][0] / clockbase
                # Convert from device ticks to time in seconds.
                t0_burst = sig_burst.header['createdtimestamp'][0] / clockbase
                t = (sig_burst.time + t0_burst) - ts0
                value = sig_burst.value[0, :]
                # Plot the data
                ax1.plot(t, value)
                ax1.set_title(f"Progress of data acquisition: {100 * progress:.2f}%.")
                fig.canvas.draw()
                plt.pause(0.001)
    return results, ts0
```

#### Execute the measurement

```python
import time

ts0 = np.nan
timeout = 1.5 * TOTAL_DURATION
start_time = time.time()
results = {x: [] for x in sample_nodes}

fig = plt.figure()
ax1 = fig.add_subplot(111)
ax1.set_xlabel("Time ($s$)")
ax1.set_ylabel("Subscribed signals")
ax1.set_xlim([0, TOTAL_DURATION])
ax1.grid()

# Start recording data
daq_module.execute()

while time.time() - start_time < timeout:
    results, ts0 = read_and_plot_data(daq_module, results, ts0)
    if daq_module.raw_module.finished():
        # Once finished, call once more to get the potential remaining data.
        results, ts0 = read_and_plot_data(daq_module, results, ts0)
        break

    time.sleep(BURST_DURATION)
```

#### Saving the data

```python
daq_module.save.save.wait_for_state_change(0, timeout=10)
```
