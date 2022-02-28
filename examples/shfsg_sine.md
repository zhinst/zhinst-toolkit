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

# Generate a sine wave

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x SHFSG

```python
from zhinst.toolkit import Session

session = Session('localhost')
device = session.connect_device("DEVXXXX")
```

### Configure center frequency and RF output

```python
device.sgchannels[0].configure_channel(
    enable=True,
    output_range=0,
    center_frequency=1e9,
    rf_path=True
)
```

### Configure digital sine generator

```python
device.sgchannels[0].configure_sine_generation(
    enable=True,
    osc_index=0,
    osc_frequency=100e6,
    phase=0,
    gains=(0.7, -0.7, 0.7, 0.7)
)
```
