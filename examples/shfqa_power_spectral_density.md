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
    display_name: Python 3.9.15 64-bit ('3.9.15')
    language: python
    name: python3
---

<!-- #region -->
# SHFQA Power spectral density (PSD)


Requirements:

* LabOne Version >= 23.02
* Instruments:
    1 x SHFQA Instrument
<!-- #endregion -->

```python
from zhinst.toolkit import Session, SHFQAChannelMode

session = Session("localhost")
device = session.connect_device("DEV12XXX")
```

### Parameter

```python
qachannel_center_frequency = 7.1e9
qachannel_power_in = -30
qachannel_power_out = qachannel_power_in

main_channel_idx = 0 # The PSD is measured on the main channel
test_signal_channel_idx = 1 # A second channel of the SHFQA will be used to generate a test signal
```

## Sweeper configuration


Define some genral settings of the sweeper

```python
sweeper = session.modules.shfqa_sweeper
sweeper.device(device)

sweeper.rf.channel(main_channel_idx)
sweeper.rf.center_freq(qachannel_center_frequency)
sweeper.rf.input_range(qachannel_power_in)
sweeper.rf.output_range(qachannel_power_out)

sweeper.sweep.start_freq(-700e6)
sweeper.sweep.stop_freq(700e6)
sweeper.sweep.num_points(101)
sweeper.sweep.mapping("linear")
sweeper.sweep.oscillator_gain(0.7)

# Note: long integration times are expected to give a better result for power
# spectral denisty measurements.
sweeper.average.integration_time(1e-3)

# Note: The PSD feature supports hardware averages
sweeper.average.num_averages(100)
sweeper.average.mode("cyclic")
```

Enable the power spectral density (PSD) feature. When the PSD feature is enabled, the device computes the square of the absolute values of the integration results before averaging the results.

```python
sweeper.sweep.psd(True)
```

## Configure the test signal channel


## Measure power spectral density


## Measurement


### PSD measurement without test signal


As for the normal spectroscopy, the PSD feature performs frequency sweep of the oscillator signal that gets multplied with the input signal before the integration. But as opposed to normal spectroscopy measurement where we would use the same oscillator as probe signal at the output, the PSD is usually measured for a static external signal. Therefore we should make sure that the output of the QA channel is switched off and only the input is switched on.

```python
device.qachannels[main_channel_idx].input.on(True)
device.qachannels[main_channel_idx].output.on(False)
```

First, we also switch off the test signal on the other QC channel in order 

```python
device.qachannels[main_channel_idx].output.on(False)
```

Now that everything is prepared, we can run the first PSD measurement

```python
psd_off = sweeper.run()
```

```python
# use sweeper plotting function
sweeper.plot()
```

### PSD measurement with test signal


# Analyze results

```python

```
