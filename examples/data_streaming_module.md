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
import matplotlib.pyplot as plt
import pandas
```

## General configuration

### Connection to the instrument

```python
### UHFLI, VHFLI, GHFLI, SHFLI
device_id = "DEVXXXX"
device_interface = "1GbE" # "1GbE" or "USB"
data_server_host = "localhost"

### MFLI, MFIA
# device_id = "DEVXXXX"
# device_interface = "PCIe"
# data_server_host = f"mf-{device_id}"

### For all instruments except HF2LI
is_hf2 = False

### HF2LI
# device_id = "DEVXXXX"
# device_interface = "USB"
# data_server_host = "localhost"
# is_hf2 = True

### Connection
session = Session(data_server_host, hf2=is_hf2)
device = session.connect_device(device_id, interface=device_interface)

print(f"The API client is connected to {device.serial.upper()} of type {device.device_type} via the data server with the following version:")
print(f"Client: {session.about.version()}")
print(f"Server: {session.daq_server.getString('/zi/about/version')}")
```

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

## Data Streaming module

### General configuration

#### Instantiation

```python
stream = session.modules.data_streaming
```

#### Signal paths to record

```python
signal_paths = [
    f"/{device.serial}/demods/0/sample.x",
    f"/{device.serial}/demods/0/sample.y",
    f"/{device.serial}/demods/0/sample.r",
]
stream.subscribe(signal_paths)
```

#### Data saving settings

```python
stream.save.fileformat("hdf5")  # Possible formats are "csv", "mat" (MATLAB) or "hdf5"
stream.save.filename(f"data_streaming_module_{device.serial}")
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

#### Extract and plot signals

```python
ts = data[f"/{device.serial}/timestamp"]
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
while time.time() - start_time < timeout_sec:
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

## Tear down

```python
session.daq_server.disconnect()
del session
```
