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

# PWA & Boxcar

This example demonstrates how to connect to a Zurich Instruments UHF Lock-in 
Amplifier and obtain output from the Input PWA and Boxcar.

Connect to a Zurich Instruments UHF Lock-in Amplifier and
obtain Input PWA and Boxcar data via poll-command.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x UHF Instrument with BOX option

```python
import time
import numpy as np
from zhinst.toolkit import Session, PollFlags

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### Instrument configuration

```python
OUT_CHANNEL = 0
OUT_MIXER_CHANNEL = 3
IN_CHANNEL = 0
OSC_INDEX = 0
FREQUENCY = 9.11e6
BOXCAR_INDEX = 0
INPUTPWA_INDEX = 0
AMPLITUDE = 0.5
WINDOW_START = 75
WINDOWSIZE = 3e-9
PERIODS_VALUES = np.logspace(0, 9, 10, base=2)
```

```python
with device.set_transaction():
    device.sigins[IN_CHANNEL].imp50(1)
    device.sigins[IN_CHANNEL].ac(0)
    device.sigins[IN_CHANNEL].range(2 * AMPLITUDE)

    device.inputpwas[INPUTPWA_INDEX].oscselect(OSC_INDEX)
    device.inputpwas[INPUTPWA_INDEX].inputselect(IN_CHANNEL)
    device.inputpwas[INPUTPWA_INDEX].mode(1)
    device.inputpwas[INPUTPWA_INDEX].shift(0.0)
    device.inputpwas[INPUTPWA_INDEX].harmonic(1)
    device.inputpwas[INPUTPWA_INDEX].enable(True)

    device.boxcars[BOXCAR_INDEX].oscselect(OSC_INDEX)
    device.boxcars[BOXCAR_INDEX].inputselect(IN_CHANNEL)
    device.boxcars[BOXCAR_INDEX].windowstart(WINDOW_START)
    device.boxcars[BOXCAR_INDEX].windowsize(WINDOWSIZE)
    device.boxcars[BOXCAR_INDEX].limitrate(1e3)
    device.boxcars[BOXCAR_INDEX].periods(PERIODS_VALUES[0])
    device.boxcars[BOXCAR_INDEX].enable(True)

    device.oscs[OSC_INDEX].freq(FREQUENCY)
    device.sigouts[OUT_CHANNEL].on(True)
    device.sigouts[OUT_CHANNEL].enables[OUT_MIXER_CHANNEL](1)
    device.sigouts[OUT_CHANNEL].range(1)
    device.sigouts[OUT_CHANNEL].amplitudes[OUT_MIXER_CHANNEL](AMPLITUDE)

# Wait for boxcar output to settle
time.sleep(PERIODS_VALUES[0] / FREQUENCY)
```

Get the values that are actually set on the device

```python
frequency_dev = device.oscs[OSC_INDEX].freq()
windowstart_dev = device.boxcars[BOXCAR_INDEX].windowstart()
windowsize_dev = device.boxcars[BOXCAR_INDEX].windowsize()
```

### Subscribing to nodes

```python
boxcar_sample_node = device.boxcars[BOXCAR_INDEX].sample
boxcar_periods_node = device.boxcars[BOXCAR_INDEX].periods
inputpwa_node = device.inputpwas[INPUTPWA_INDEX].wave

boxcar_sample_node.subscribe()
boxcar_periods_node.subscribe()
inputpwa_node.subscribe()
```

### Polling the data

Use `get_as_event` to ensure first period values

```python
boxcar_periods_node.get_as_event()

for periods in PERIODS_VALUES:
    time.sleep(0.5)
    boxcar_periods_node(int(periods))
    boxcar_periods_node.wait_for_state_change(int(periods))
```

```python
data = session.poll(recording_time=0.1, timeout=0.5, flags=PollFlags.DEFAULT)
device.unsubscribe()
```

```python
sample = data[boxcar_sample_node]

boxcar_value = sample["value"]
boxcar_timestamp = sample["timestamp"]
boxcar_periods_value = data[boxcar_periods_node]["value"]
boxcar_periods_timestamp = data[boxcar_periods_node]["timestamp"]
print(f"Measured average boxcar amplitude is {np.mean(boxcar_value):.5e} V.")
```

Convert timestamps from ticks to seconds via clockbase

```python
clockbase = device.clockbase()

boxcar_t = (boxcar_timestamp - boxcar_timestamp[0]) / clockbase
boxcar_periods_t = (boxcar_periods_timestamp - boxcar_periods_timestamp[0]) / clockbase
boxcar_periods_t[0] = boxcar_t[0]
```

### Plot the data

```python
import matplotlib.pyplot as plt
```

#### Boxcar output

```python
_, ax1 = plt.subplots()

ax1.grid(True)
ax1.set_xlim(
    min(boxcar_t[0], boxcar_periods_t[0]),
    max(boxcar_t[-1], boxcar_periods_t[-1]),
)
ax1.set_xlabel("Time (s)")
ax1.set_ylabel("Boxcar value (V)")
ax1.set_title("Boxcar output: The effect of averaging\nperiods on the boxcar value")
ax1.plot(boxcar_t, boxcar_value, label="boxcar output")
ax1.legend(loc=4)

ax2 = ax1.twinx()
ax2.step(
    np.append(boxcar_periods_t, boxcar_t[-1]),
    np.append(boxcar_periods_value, boxcar_periods_value[-1]),
    "-r",
    label="Averaging periods",
)
ax2.set_yscale("log")
ax2.set_ylabel("Number of Averaging Periods")
ax2.legend(loc=1)
plt.plot()
```

#### Input PWA waveform

```python
pwa_wave = data[inputpwa_node][-1]
pwa_wave["binphase"] = pwa_wave["binphase"] * 360 / (2 * np.pi)
windowsize_set_degrees = 360 * frequency_dev * windowsize_dev
phase_window = (pwa_wave["binphase"] >= windowstart_dev) & (
    pwa_wave["binphase"] <= windowstart_dev + windowsize_set_degrees
)
```

```python
_, axis = plt.subplots()

axis.grid(True)
axis.axhline(0, color="k")
# The inputpwa waveform is stored in 'x', currently 'y' is unused.
axis.plot(pwa_wave["binphase"], pwa_wave["x"])
axis.fill_between(
    pwa_wave["binphase"], 0, pwa_wave["x"], where=phase_window, alpha=0.5
)
axis.set_xlim(0, 360)
title = "Input PWA waveform, the shaded region shows the portion\n of the " \
    "waveform the boxcar is integrating."
axis.set_title(title)
axis.set_xlabel("Phase (degrees)")
axis.set_ylabel("Amplitude (V)")
plt.plot()
```
