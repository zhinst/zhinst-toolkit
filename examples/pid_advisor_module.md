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

# PID Advisor Module

Demonstrate how to connect to a Zurich Instruments Lock-in Amplifier and use
the PID Advisor to set up an internal PLL control loop.
Connect to a Zurich Instruments Lock-in Amplifier and obtain optimized
P, I, and D parameters for an internal PLL loop.

Requirements:

* LabOne Version >= 22.08
* Instruments:
    1 x UHF or an MF with the PID Option
* signal output 1 connected to signal input 1 with a BNC cable.

```python
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

```python
with open("test.json", "w") as f:
    import json
    f.write(json.dumps(json.loads(session.modules.pid_advisor.raw_module.listNodesJSON("*"))))
```

This example additionally requires two oscillators. For MF devices, this means,
that the `MD` option needs to be installed.

```python
if device.device_type.startswith("MF") and "MD" not in device.device_options:
    raise RuntimeError(
        "Required option set not satisfied. On MF Instruments this example "
        f"requires both the PID and the MD Option. Device `{device}` reports "
        f"devtype `{device.device_type}` and options `{device.device_options}`."
    )
```

### Instrument settings

```python
OSC_INDEX = 0
OUT_CHANNEL = 0
PID_INDEX = 0
CENTER_FREQUENCY_HZ = 400e5
OUT_MIXER_CHANNEL = 1  # UHFLI: 3, HF2LI: 6, MFLI: 1

with device.set_transaction():
    device.oscs[OSC_INDEX].freq(CENTER_FREQUENCY_HZ)

    device.sigouts[OUT_CHANNEL].on(True)
    device.sigouts[OUT_CHANNEL].range(1.0)
    device.sigouts[OUT_CHANNEL].enables[OUT_MIXER_CHANNEL](True)
    device.sigouts[OUT_CHANNEL].amplitudes[OUT_MIXER_CHANNEL](1.0)

    device.pids[PID_INDEX].input("demod_theta")
    device.pids[PID_INDEX].inputchannel(0)
    device.pids[PID_INDEX].setpoint(0)
    device.pids[PID_INDEX].output("oscillator_frequency")
    device.pids[PID_INDEX].outputchannel(OSC_INDEX) # Oscillator controlled by PID.
    device.pids[PID_INDEX].center(CENTER_FREQUENCY_HZ)
    device.pids[PID_INDEX].enable(False)
    device.pids[PID_INDEX].phaseunwrap(True)
    device.pids[PID_INDEX].limitlower(-100e5)
    device.pids[PID_INDEX].limitupper(100e5)
```

### PID module setup 

```python
from zhinst.toolkit import PIDMode
pid_advisor = session.modules.pid_advisor

pid_advisor.device(device)
# Turn off auto-calc on param change. Enabled auto calculation can be used to
# automatically update response data based on user input.
pid_advisor.auto(False)

pid_advisor.pid.targetbw(10e3)
pid_advisor.pid.mode(PIDMode.P_Gain | PIDMode.I_Gain | PIDMode.D_Gain)
pid_advisor.index(PID_INDEX)

pid_advisor.dut.source("internal_pll")
# IO Delay of the feedback system describing the earliest response for a step
# change. This parameter does not affect the shape of the DUT transfer function.
pid_advisor.dut.delay(0.0)
# Other DUT parameters (not required for the internal PLL model)
# pid_advisor.set.dut.gain(1.0)
# pid_advisor.set.dut.bw(1000)
# pid_advisor.set.dut.fcenter(15e6)
# pid_advisor.set.dut.damping(0.1)
# pid_advisor.set.dut.q(10e3)

# Start values for the PID optimization.
# Zero values will imitate a guess. Other values can be used as hints for the
# optimization process.
pid_advisor.pid.p(0)
pid_advisor.pid.i(0)
pid_advisor.pid.d(0)

# Start the module thread
pid_advisor.execute()
```

### Advise

Setup logging to see the progress of the `wait_done` function.

```python
import logging
import sys

handler = logging.StreamHandler(sys.stdout)
logging.getLogger("zhinst.toolkit").setLevel(logging.INFO)
logging.getLogger("zhinst.toolkit").addHandler(handler)
```

```python
pid_advisor.calculate(True)
print("Starting advising. Optimization process may run up to a minute...")
pid_advisor.wait_done()
```

```python
print("The pidAdvisor calculated the following gains:")
print(f"P: {pid_advisor.pid.p()}")
print(f"I: {pid_advisor.pid.i()}")
print(f"D: {pid_advisor.pid.d()}")
```

If the values match the expectation, they can be uploaded to the device.
Otherwise, the advice step can be repeated.

```python
pid_advisor.todevice(True)
```

### Plot the result

```python
import matplotlib.pyplot as plt
import numpy as np

bode_result = pid_advisor.bode()
step_result = pid_advisor.step()
step_x = step_result["x"]
step_grid = pid_advisor.step()["grid"]
bw_advisor = pid_advisor.bw()

bode_complex_data = bode_result["x"] + 1j * bode_result["y"]
bode_grid = bode_result["grid"]

_, axes = plt.subplots(2, 1)
axes[0].plot(bode_grid, 20 * np.log10(np.abs(bode_complex_data)))
axes[0].set_xscale("log")
axes[0].grid(True)
axes[0].set_title(
    f"Model response for internal PLL with\n"
    f"P = {pid_advisor.pid.p():.4f}, I = {pid_advisor.pid.i():.4f},\n"
    f"D = {pid_advisor.pid.d():.4f} and bandwidth {(bw_advisor * 1e-3):.4f} kHz"
)
axes[0].set_ylabel("Bode Gain (dB)")
axes[0].autoscale(enable=True, axis="x", tight=True)

axes[1].plot(bode_grid, np.angle(bode_complex_data) / np.pi * 180)
axes[1].set_xscale("log")
axes[1].grid(True)
axes[1].set_xlabel("Frequency (Hz)")
axes[1].set_ylabel("Bode Phase (deg)")
axes[1].autoscale(enable=True, axis="x", tight=True)

_, axis = plt.subplots(1, 1)
axis.plot(step_grid * 1e6, step_x)
axis.grid(True)
axis.set_title(
    f"Step response for internal PLL with\n"
    f"P = {pid_advisor.pid.p():.4f}, I = {pid_advisor.pid.i():.4f},\n"
    f"D = {pid_advisor.pid.d():.4f} and bandwidth {(bw_advisor * 1e-3):.4f} kHz"
)
axis.set_xlabel("Time (μs)")
axis.set_ylabel("Step Response")
axis.autoscale(enable=True, axis="x", tight=True)
axis.set_ylim([0.0, 1.05])
plt.draw()
plt.show()

```
