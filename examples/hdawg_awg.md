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

# Uploading and running an AWG program

Demonstrate how to connect to a Zurich Instruments HDAWG, upload and run an AWG program.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x HDAWG

```python
from zhinst.toolkit import Session
import numpy as np

session = Session('localhost')
device = session.connect_device("DEVXXXX")
```

### Base configuration

```python
OUT_CHANNEL = 0
AWG_CHANNEL = 0

device.system.awg.channelgrouping(0)

with device.set_transaction():
    device.sigouts[OUT_CHANNEL].on(True)
    device.sigouts[OUT_CHANNEL].range(1)
    device.awgs[0].outputs[AWG_CHANNEL].amplitude(1.0)
    device.awgs[0].outputs[AWG_CHANNEL].modulation.mode(0)
    device.awgs[0].time(0)
    device.awgs[0].userregs(0)
```

### Configuring the AWG program

```python
import textwrap
AWG_N = 2000

awg_program = textwrap.dedent(f"""
        const AWG_N = {AWG_N};
        wave w0 = gauss(AWG_N, AWG_N/2, AWG_N/20);
        wave w1 = placeholder(AWG_N);
        wave w2 = zeros(AWG_N);
        wave w3 = placeholder(AWG_N);
        assignWaveIndex(1, w1, 1);
        assignWaveIndex(1, w3, 3);
        while(getUserReg(0) == 0) {
        setTrigger(1);
        setTrigger(0);
        playWave(w0);
        playWave(w1);
        playWave(w2);
        playWave(w3);
        }
""")
device.awgs[0].load_sequencer_program(awg_program)
```

#### Write the waveforms into the device memory

```python
from zhinst.toolkit import Waveforms

waveforms = Waveforms()
waveforms.assign_waveform(
    slot=1,
    wave1=np.sin(np.linspace(0, 2 * np.pi, AWG_N))
)
waveforms.assign_waveform(
    slot=3,
    wave1=-1.0 * np.blackman(AWG_N)
)
device.awgs[0].write_to_waveform_memory(waveforms)
```

### Run the program

```python
device.awgs[0].single(True)
device.awgs[0].enable(True)
```
