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

# Generate a sine wave with the SHFSG
Generate a sinusoidal signal at a single frequency using the sine generator functionality of the SHFSG.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x SHFSG

```python
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
```

The SHFSG is able to generate signals at frequencies up to 8.5 GHz. To do so, it firstly uses a digital sine generator to produce a sinusoidal signal al low frequencies, and then operates frequency up-conversion to bring the frequency in the RF domain.
### Configure center frequency and RF output
Configure the center frequency used in the up-conversion and the RF output power range.

```python
device.sgchannels[0].configure_channel(
    enable=True,
    output_range=0,
    center_frequency=1e9,
    rf_path=True
)
```

### Configure digital sine generator
Configure the digital sine generator by specifying which oscillator should be used, the frequency and the phase of the generated sine and the gains of the outputs, which will determine the amplitude of the signal (see https://docs.zhinst.com/shfsg_user_manual/tutorial_modulation.html for a reference about the output gains).

```python
device.sgchannels[0].configure_sine_generation(
    enable=True,
    osc_index=0,
    osc_frequency=100e6,
    phase=0,
    gains=(0.7, -0.7, 0.7, 0.7)
)
```
