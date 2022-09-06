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

# HF2LI

The Zurich Instruments HF2LI is a digital lock-in amplifier covering the
frequency range between DC and 50 MHz. It is one of the first instrument
developed by Zurich Instruments. Since the initial release of the HF2 a lot more
Instruments have joined the family of Zurich Instrument and the features of
LabOne where constantly upgraded. Never the less the HF2LI offers exceptional
features and measurement performance and is of course still fully supported by
LabOne and zhinst-toolkit. However it has a few specialties like a separate
Data Sever or the maximal support of API level 1.

Never the less toolkit offers a similar handling of the HF2 compared to other
devices. Since the HF2 uses a different data server one can not share a session
with other devices.

```python
from zhinst.toolkit import Session

session = Session("localhost", hf2=True)
```

The flag ``hf2`` indicates that the session should be established with the HF2
data server.

> Note:
>
> Instead of the flag one can also specify the port of the HF2 server directly,
> e.g. Session("10.42.0.92", 8005). It results in the same session but the
> HF2 flag helps to differentiate the session from a Session to the data server
> for the other devices.

```python
device = session.connect_device("DEVXXXX")
```

The created device object has the same functionality than all other device and
holds the nodetree for the device. (for more information about the nodetree
refer to the first steps)

```python
list(device.child_nodes())
```

```python
device.demods[0].enable(1)
device.demods[0].enable()
```

## Polling DEMOD Samples

To get samples for the device subscribe and poll is the preferred way.
After the subscribe command the data server will the node changes in an
internally. In case of a sample node the values will be updated by the device in
the respective sampling frequency. With the poll command the buffered data can
be fetched.

> Note:
>
> The poll command is implemented at the session level since it returns all
> subscribed data within a session. It is not possible to poll only a single
> node if multiple nodes are subscribed.

```python
import time
device.demods[0].sample.subscribe()
time.sleep(1)
device.demods[0].sample.unsubscribe()
poll_result = session.poll()
demod_sample = poll_result[device.demods[0].sample]
```

```python
import matplotlib.pyplot as plt

_, axis = plt.subplots(1, 1)
axis.plot(demod_sample["x"])
axis.grid(True)
axis.set_title("X Data from the polled demod sample")
axis.set_xlabel("Sample")
axis.set_ylabel("Value")
plt.show()
```

## PID Advisor

Demonstrate how to connect to a Zurich Instruments HF2 Lock-in Amplifier and use
the PID Advisor to set up an internal PLL control loop using the pid_advisor
module.

### Device Settings

```python
OUT_MIXER_CHANNEL = 6
with device.set_transaction():
    device.oscs[0].freq(1e6)
    device.sigouts[0].on(True)
    device.sigouts[0].enables[OUT_MIXER_CHANNEL](True)
    device.sigouts[0].range(1.0)
    device.sigouts[0].amplitudes[OUT_MIXER_CHANNEL](1.0)
```

### PID Advisor Module Settings

```python
pid_advisor = session.modules.pid_advisor
pid_advisor.device(device)
# Turn off auto-calc on param change. Enabled auto calculation can be used to
# automatically update response data based on user input.
pid_advisor.auto(False)
# Target bandwidth (Hz).
pid_advisor.pid.targetbw(10e3)
# PID advising mode (bit coded)
# bit 0: optimize/tune P
# bit 1: optimize/tune I
# bit 2: optimize/tune D
# Example: mode = 7: Optimize/tune PID
pid_advisor.pid.mode(7)
# PID index to use (first PLL of device: 0)
pid_advisor.index(0)
```

### DUT Settings

```python
# DUT model
# source = 1: Lowpass first order
# source = 2: Lowpass second order
# source = 3: Resonator frequency
# source = 4: Internal PLL
# source = 5: VCO
# source = 6: Resonator amplitude
dut_source = 4
pid_advisor.dut.source(dut_source)
if dut_source == 4:
    # HF2: Since the PLL and PID are 2 separate hardware units on the device, we need to
    # additionally specify that the PID Advisor should model the HF2's PLL.
    pid_advisor.pid.type("pll")
    # Note: The PID Advisor is appropriate for optimizing the HF2's PLL parameters (pid/type set
    # to 'pll') or the HF2's PID parameters (pid/type set to 'pid').
else:
    # Other DUT parameters (not required for the internal PLL model)
    pid_advisor.dut.gain(1.0)
    pid_advisor.dut.bw(1000)
    pid_advisor.dut.fcenter(15e6)
    pid_advisor.dut.damping(0.1)
    pid_advisor.dut.q(10e3)

# IO Delay of the feedback system describing the earliest response
# for a step change. This parameter does not affect the shape of
# the DUT transfer function
pid_advisor.dut.delay(0.0)
```

### Run

```python
# Start values for the PID optimization. Zero
# values will imitate a guess. Other values can be
# used as hints for the optimization process.
pid_advisor.pid.p(0)
pid_advisor.pid.i(0)
pid_advisor.pid.d(0)

# Start the module thread
pid_advisor.execute()
pid_advisor.calculate(1)
pid_advisor.wait_done(timeout=1000)

# print results
p_advised = pid_advisor.pid.p()
i_advised = pid_advisor.pid.i()
d_advised = pid_advisor.pid.d()
print(
    f"The pidAdvisor calculated the following gains, P: {p_advised}, I: {i_advised}, "
    f"D: {d_advised}."
)
```

### Plot

#### Bode Diagram

```python
import matplotlib.pyplot as plt
import numpy as np

bode_result = pid_advisor.bode()
bode_complex_data = bode_result["x"] + 1j * bode_result["y"]
bw_advisor = pid_advisor.bw()

_, axes = plt.subplots(2, 1)
axes[0].plot(bode_result["grid"], 20 * np.log10(np.abs(bode_complex_data)))
axes[0].set_xscale("log")
axes[0].grid(True)
axes[0].set_title(
    "Model response for internal PLL with "
    f"P = {p_advised:.1f}, I = {i_advised:.1f},\n"
    f"D = {d_advised:.5f} and bandwidth {(bw_advisor * 1e-3):.1f} kHz"
)
axes[0].set_ylabel("Bode Gain (dB)")
axes[0].autoscale(enable=True, axis="x", tight=True)

axes[1].plot(bode_result["grid"], np.angle(bode_complex_data) / np.pi * 180)
axes[1].set_xscale("log")
axes[1].grid(True)
axes[1].set_xlabel("Frequency (Hz)")
axes[1].set_ylabel("Bode Phase (deg)")
axes[1].autoscale(enable=True, axis="x", tight=True)
plt.show()
```

#### Step Response

```python
import matplotlib.pyplot as plt

step_result = pid_advisor.step()
_, axis = plt.subplots(1, 1)
axis.plot(step_result["grid"] * 1e6, step_result["x"])
axis.grid(True)
axis.set_title(
    "Step response for internal PLL with "
    f"P = {p_advised:0.1f}, I = {i_advised:0.1f},\n"
    f"D = {d_advised:0.5f} and bandwidth {(bw_advisor * 1e-3):.1f} kHz"
)
axis.set_xlabel(r"Time ($\mu$s)")
axis.set_ylabel(r"Step Response")
axis.autoscale(enable=True, axis="x", tight=True)
axis.set_ylim([0.0, 1.05])
plt.show()
```

### Upload values to devices

```python
pid_advisor.todevice(1)
```

```python

```
