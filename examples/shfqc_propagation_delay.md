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

<!-- #region -->
# Determine propagation delay


Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x SHFQC Instrument
<!-- #endregion -->

```python
from zhinst.toolkit import Session, SHFQAChannelMode

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### Parameter

```python
qachannel_center_frequency = 4.1e9
qachannel_power_in = 5
qachannel_power_out = 0

max_amplitude_readout = 0.8
```

<!-- #region tags=[] -->
## Device configuration
<!-- #endregion -->

```python
device.qachannels[0].configure_channel(
    center_frequency=qachannel_center_frequency,
    input_range=qachannel_power_in,
    output_range=qachannel_power_out,
    mode=SHFQAChannelMode.SPECTROSCOPY,
)
```

<!-- #region tags=[] -->
## Prepare readout pulse at one frequency
<!-- #endregion -->

```python
from shfqc_helper import generate_flat_top_gaussian
from zhinst.utils.shfqa import SHFQA_SAMPLING_FREQUENCY

envelope_duration = 1.0e-6
envelope_rise_fall_time = 0.05e-6
envelope_frequencies = [100e6]

probe_pulse = generate_flat_top_gaussian(
    envelope_frequencies,
    envelope_duration,
    envelope_rise_fall_time,
    SHFQA_SAMPLING_FREQUENCY,
    scaling=0.95,
)

device.qachannels[0].spectroscopy.envelope.wave(probe_pulse[0])

```

## Take propagation delay measurement

```python
from shfqc_helper import set_trigger_loopback, clear_trigger_loopback
spectroscopy_delay = 0
pulse_envelope = probe_pulse[0]
envelope_delay = 0
scope_channel = 0
num_avg = 2**16

trigger_input = "channel0_trigger_input0"
# trigger_input = "software_trigger0"
loopback = True

# Enable the loopback trigger
if loopback:
    set_trigger_loopback(session, device, rate=500e3)

# Generate the complex pulse envelope with a modulation frequency at the
# readout frequency of qubit
with device.set_transaction():
    device.qachannels[0].spectroscopy.delay(spectroscopy_delay)
    device.qachannels[0].spectroscopy.envelope.delay(0)
    device.qachannels[0].spectroscopy.envelope.wave(pulse_envelope)
    device.qachannels[0].spectroscopy.trigger.channel(0)
    device.qachannels[0].spectroscopy.envelope.enable(1)
    device.qachannels[0].input.on(1)
    device.qachannels[0].output.on(1)
    device.qachannels[0].oscs[0].freq(0)


# Measure the generated pulse with the SHFQA scope.
margin_seconds = 400e-9
segment_duration = envelope_duration + margin_seconds
device.scopes[0].configure(
    input_select={scope_channel: f"channel0_signal_input"},
    num_samples=int(segment_duration * SHFQA_SAMPLING_FREQUENCY),
    trigger_input=trigger_input,
    num_segments=1,
    num_averages=num_avg,
    trigger_delay=envelope_delay,
)
device.scopes[0].run(single=True)

# Issue {num_avg} triggers if needed
if trigger_input == "software_trigger0":
    for _ in range(num_avg):
        device.system.swtriggers[0].single(1)

scope_trace, *_ = device.scopes[0].read(timeout=5)

if loopback:
    clear_trigger_loopback(session, device)

device.qachannels[0].input.on(0)
device.qachannels[0].output.on(0)
```

## Plot measured pulse trace

```python
import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure(figsize=(24,10))
time_ticks_us = 1.0e6 * np.array(range(len(scope_trace[0]))) / SHFQA_SAMPLING_FREQUENCY
plt.plot(time_ticks_us, np.real(scope_trace[0]))
plt.plot(time_ticks_us, np.imag(scope_trace[0]))
plt.title("Resonator probe pulse", fontsize=30)
plt.xlabel(r"t [$\mu$s]", fontsize=20)
plt.ylabel("scope samples [V]", fontsize=20)
plt.legend(["real", "imag"], fontsize=20)
plt.grid()
plt.show()
```
