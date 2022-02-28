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

# Precompensation curve fit

Demonstrate how to connect to a Zurich Instruments HDAWG and
use the precompensation module to fit filter parameters for a
measured signal.

Connect to a Zurich Instruments HDAWG. The example uploads a signal to
the precompensationAdvisor module and reads back the filtered signal. This functionality
is used to feed a fitting algorithm for fitting filter parameters.

Requirements:

* LabOne Version >= 22.02
* Instruments:
    1 x HDAWG Instrument

```python
import numpy as np
from scipy import signal
from lmfit import Model

from zhinst.toolkit import Session

session = Session('localhost')
device = session.connect_device("DEVXXXX")
```

### Generate signals

```python
SAMPLING_RATE = 2.4e9
```

#### Generate target signal

```python
MIN_X = -96
MAX_X = 5904
x_values = np.array(range(MIN_X, MAX_X))
x_values = [element / SAMPLING_RATE for element in x_values]
target_signal = np.array(np.concatenate((np.zeros(-MIN_X), np.ones(MAX_X))))
```

#### Generate actual signal

Generate "actual signal" through filtering the initial signal with an exponential filter and add noise

```python
TAU = 100e-9
AMPL = 0.4

# calculate a and b from amplitude and tau
alpha = 1 - np.exp(-1 / (SAMPLING_RATE * TAU * (1 + AMPL)))
if AMPL >= 0.0:
    k = AMPL / (1 + AMPL - alpha)
    signal_a = [(1 - k + k * alpha), -(1 - k) * (1 - alpha)]
else:
    k = -AMPL / (1 + AMPL) / (1 - alpha)
    signal_a = [(1 + k - k * alpha), -(1 + k) * (1 - alpha)]
signal_b = [1, -(1 - alpha)]

distorted_signal = np.array(
    signal.lfilter(signal_b, signal_a, target_signal)
    + 0.01 * np.random.normal(size=target_signal.size)
)
```

### Prepare precompensationAdvisor module

```python
precomp_module = session.modules.precompensation_advisor
precomp_module.device(device)

precomp_module.exponentials[0].enable(True)
precomp_module.wave.input.source(3)
device.system.clocks.sampleclock.freq(SAMPLING_RATE)
```

### Fitting the model parameters

```python
def get_precompensated_signal(module_handle, input_signal, amplitude, timeconstant):
    """Uploads the input_signal to the precompensationAdvisor module and 
    returns the simulated forward transformed signal with an exponential 
    filter (amplitude, timeconstant).
    """
    module_handle.exponentials[0].amplitude(amplitude)
    module_handle.exponentials[0].timeconstant(timeconstant)
    module_handle.wave.input.inputvector(input_signal)
    forward_wave = precomp_module.wave.output.forwardwave()
    return np.array(forward_wave["x"])

gmodel = Model(
    get_precompensated_signal, independent_vars=["module_handle", "input_signal"]
)
result = gmodel.fit(
    target_signal,
    input_signal=distorted_signal,
    module_handle=precomp_module,
    amplitude=0.0,
    timeconstant=1e-4,
    fit_kws={"epsfcn": 1e-3},
)
```

### Plot results

```python
import matplotlib.pyplot as plt

_, axis = plt.subplots()
axis.plot(x_values, result.init_fit, "k", label="initial")
axis.plot(x_values, result.best_fit, "r", label="fitted")
axis.plot(x_values, target_signal, "b", label="target")
axis.legend()
axis.ticklabel_format(axis="both", style="sci", scilimits=(-2, 2))
axis.set_xlabel("time [s]")
axis.set_ylabel("Amplitude")
plt.title('Signals')
plt.grid()
plt.show()
```
