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

# Impedance Module

Demonstrate how the LabOne Impedance Module can be used to do a user
compensation (calibration).

Requirements:

* LabOne Version >= 22.08
* Instruments:
    1 x Instrument with IA option

```python
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

### Instrument settings

```python
with device.set_transaction():
    device.imps[0].enable(1)
    device.imps[0].mode(0)
    device.imps[0].auto.output(1)
    device.imps[0].auto.bw(1)
    device.imps[0].auto.inputrange(1)
    device.imps[0].freq(1000)
    device.imps[0].output.amplitude(0.3)
    device.imps[0].output.range(1)
    device.imps[0].model(0)
```

### User compensation setup

```python
module = session.modules.impedance

# Start the module
module.execute()

module.device(device)
# Set frequency range from 1000 to 5000000 with 20 number of samples
module.freq.start(1000)
module.freq.stop(5000000)
module.freq.samplecount(20)
# Disabling the validation for demonstration prupose.
# (this allows everything to pass, in case the short is much higher than 0 Ohm.)
module.validation(0)
# Short only mode with additional open step
# 1 = Short
# 4 = Load
# 5 = Short Load
# 8 = Load Load Load
module.mode(1)
```

Set up the logging to track the progress of the calibration

```python
import logging
import sys

handler = logging.StreamHandler(sys.stdout)
logging.getLogger("zhinst.toolkit").setLevel(logging.INFO)
logging.getLogger("zhinst.toolkit").addHandler(handler)
```

### Short compensation

The first compensation step is the `Short` step.

```python
step = 0
module.step(step)
module.calibrate(True)
module.wait_done(step=step, sleep_time=2)
```

Log messages from the impedance module during the first (short) calibration step.

```python
import html
print(html.unescape(module.message()))
```

### Open compensation
Please change from short into open now.

```python
step = 1
module.step(step)
module.calibrate(True)
module.wait_done(step=step, sleep_time=2)
```

Log messages from the impedance module during the second (open) calibration step.

```python
import html
print(html.unescape(module.message()))
```

### Save and upload compensation file

```python
module.todevice(True)
```

```python
from pathlib import Path

target_path = Path("testcal")
module.directory(target_path.parent)
module.filename(target_path.stem)
module.save(True)

# Use this to apply the just finished short-open compensation
# module.load(True)
```
