---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: "1.3"
      jupytext_version: 1.14.1
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# Data Streaming
Example for the Data Streaming module. This example demonstrates how to record data from an instrument continuously for a given duration including saving the data to file. The data is in a format that can be easily loaded into a Pandas data frame.

Requirements:

- LabOne version >= 26.01
- `zhinst` version >= 26.01
- 1 Instrument with at least 1 Demodulator


```python
from zhinst.toolkit import Session
from pathlib import Path
import time
import os
import matplotlib.pyplot as plt
import pandas
```

## General configuration

### Connection to the instrument


```python
### UHFLI, VHFLI, GHFLI, SHFLI
device_id = "dev13016"
device_interface = "1GbE" # "1GbE" or "USB"
data_server_host = "127.0.0.1"

### MFLI, MFIA
# device_id = "dev4696"
# device_interface = "PCIe"
# data_server_host = f"mf-{device_id}"

### For all instruments except HF2LI
is_hf2 = False

### HF2LI
# device_id = "dev878"
# device_interface = "USB"
# data_server_host = "127.0.0.1"
# is_hf2 = True

### Connection
session = Session(data_server_host, hf2=is_hf2)
device = session.connect_device(device_id, interface=device_interface)

devtype = device.features.devtype()
print(f"The API client is connected to {device_id.upper()} of type {devtype} via the data server with the following version:")
print(f"Client: {session.about.version()}")
print(f"Server: {session.daq_server.getString('/zi/about/version')}")
```

    The API client is connected to DEV4696 of type MFLI via the data server with the following version:
    Client: 26.01
    Server: 26.01
    

### Device settings


```python
data_rate_nominal = 2000
with device.set_transaction():
    device.demods[0].rate(data_rate_nominal)
    device.demods[0].enable(1)

data_rate_actual = device.demods[0].rate()
print(f"Actual data rate of demodulator: {data_rate_actual:.2f} Sa/s")

clockbase = device.clockbase()
print(f"Sampling rate of device timestamp: {clockbase*1e-6:.1f} MSa/s")
```

    Actual data rate of demodulator: 1674.11 Sa/s
    Sampling rate of device timestamp: 60.0 MSa/s
    

## Data Streaming module

### General configuration

#### Instantiation


```python
stream = session.modules.data_streaming
```

#### Signal paths to record


```python
signal_paths = [
    f"/{device_id}/demods/0/sample.x",
    f"/{device_id}/demods/0/sample.y",
    f"/{device_id}/demods/0/sample.r",
]
stream.subscribe(signal_paths)
```

#### Data saving settings


```python
stream.save.fileformat("hdf5")  # Possible formats are "csv", "mat" (MATLAB) or "hdf5"
stream.save.filename(f"data_streaming_module_{device_id}")
stream.save.directory(Path(".").absolute())
```

### Finite Acquisition

#### Duration of acquisition


```python
total_duration_sec = 4.0    # Seconds
stream.duration(total_duration_sec)
```

#### Acquire signals and save data before reading


```python
timeout_sec = 1.5 * total_duration_sec
start_time = time.time()

# Acquisition
stream.execute()
while time.time() - start_time < timeout_sec:
    print(f"Progress: {stream.progress()*100:.0f}%")
    if stream.finished():
        break
    time.sleep(1.0)
print(f"Actual duration of acquisition: {stream.duration():.2f} seconds")

# Save
stream.save.save(1)
while stream.save.save():
    time.sleep(0.1)
print("Saving to file is complete.")

# Read
data = stream.read()
print("Data is available for processing.")
```

    Progress: 0%
    Progress: 14%
    Progress: 38%
    Progress: 62%
    Progress: 86%
    Progress: 100%
    Actual duration of acquisition: 4.19 seconds
    Saving to file is complete.
    Data is available for processing.
    

#### Extract and plot signals


```python
ts = data[f"/{device_id}/timestamp"]
t = (ts - ts[0]) / clockbase

fig = plt.figure()
for signal_path in signal_paths:
    plt.plot(t, data[signal_path], label=signal_path)
plt.xlabel("Time (s)")
plt.ylabel("Amplitude (V)")
plt.legend()
plt.grid()
plt.show()
```


### Record in Pandas data frames 

#### Duration of acquisition


```python
total_duration_sec = 4.0    # Seconds
stream.duration(total_duration_sec)
```

#### Save to file while reading


```python
stream.save.saveonread(1)
```


```python
df = pandas.DataFrame()

timeout_sec = 1.5 * total_duration_sec
start_time = time.time()

# Acquisition, read and save
stream.execute()
while time.time() - start_time < timeout:sec:
    print(f"Progress: {stream.progress()*100:.0f}%")
    if stream.finished():
        data = stream.read()
        df = pandas.concat([df, pandas.DataFrame(data.to_dict())])
        break
    time.sleep(1.0)
    data = stream.read()
    df = pandas.concat([df, pandas.DataFrame(data.to_dict())])
    d = data

print(f"Actual duration of acquisition: {stream.duration():.2f} seconds")
df.head(10)
```

    Progress: 0%
    Progress: 19%
    Progress: 43%
    Progress: 62%
    Progress: 86%
    Progress: 100%
    Actual duration of acquisition: 4.19 seconds
    


<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>/dev4696/demods/0/sample.r</th>
      <th>/dev4696/demods/0/sample.x</th>
      <th>/dev4696/demods/0/sample.y</th>
      <th>/dev4696/timestamp</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>3.868772e-07</td>
      <td>3.515942e-07</td>
      <td>1.614171e-07</td>
      <td>189034862787</td>
    </tr>
    <tr>
      <th>1</th>
      <td>1.033814e-07</td>
      <td>1.030174e-07</td>
      <td>-8.667469e-09</td>
      <td>189034898627</td>
    </tr>
    <tr>
      <th>2</th>
      <td>1.588005e-07</td>
      <td>-4.811051e-08</td>
      <td>-1.513373e-07</td>
      <td>189034934467</td>
    </tr>
    <tr>
      <th>3</th>
      <td>1.625529e-07</td>
      <td>5.919916e-09</td>
      <td>-1.624451e-07</td>
      <td>189034970307</td>
    </tr>
    <tr>
      <th>4</th>
      <td>2.449647e-08</td>
      <td>-2.416414e-10</td>
      <td>2.449528e-08</td>
      <td>189035006147</td>
    </tr>
    <tr>
      <th>5</th>
      <td>9.028252e-08</td>
      <td>-4.407062e-08</td>
      <td>7.879539e-08</td>
      <td>189035041987</td>
    </tr>
    <tr>
      <th>6</th>
      <td>3.612716e-08</td>
      <td>1.931878e-08</td>
      <td>-3.052796e-08</td>
      <td>189035077827</td>
    </tr>
    <tr>
      <th>7</th>
      <td>1.423860e-07</td>
      <td>1.180523e-07</td>
      <td>-7.960802e-08</td>
      <td>189035113667</td>
    </tr>
    <tr>
      <th>8</th>
      <td>1.427767e-07</td>
      <td>1.388931e-07</td>
      <td>-3.307385e-08</td>
      <td>189035149507</td>
    </tr>
    <tr>
      <th>9</th>
      <td>6.035372e-08</td>
      <td>-1.630871e-08</td>
      <td>5.810850e-08</td>
      <td>189035185347</td>
    </tr>
  </tbody>
</table>
</div>


### Endless acquisition 

#### Duration of acquisition


```python
stream.duration(0)   # Set the duration to 0 for endless acquisition
```

#### Save to file without reading


```python
stream.save.saveonly(1)
```

#### Acquisition


```python
stream.execute()
time.sleep(3.0)
stream.finish()
print(f"Acquired signals are recorded in the saved file.")
```

    Acquired signals are recorded in the saved file.
    

## Tear down


```python
session.daq_server.disconnect()
del session
```
