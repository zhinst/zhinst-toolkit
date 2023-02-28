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
# SHFQA / SHFQC Power spectral density (PSD)


Requirements:

* LabOne Version >= 23.02
* Instruments:
    1 x SHFQA or SHFQC Instrument

Note: to apply a test signal for the power spectral density measurment, connect the output of the second QA channel (SHFQA) or first SG channel (SHFQC) to the input of the first QA channel.
<!-- #endregion -->

```python
from zhinst.toolkit import Session, SHFQAChannelMode


session = Session("localhost")
device = session.connect_device("DEVXXXX")

```

### Parameter

```python
qachannel_center_frequency = 7.1e9
qachannel_power_in = -15

main_channel = 0  # The PSD is measured on the main channel

```

## Sweeper configuration


Define some genral settings of the sweeper

```python
sweeper = session.modules.shfqa_sweeper
sweeper.device(device)

sweeper.rf.channel(main_channel)
sweeper.rf.center_freq(qachannel_center_frequency)
sweeper.rf.input_range(qachannel_power_in)

sweeper.sweep.start_freq(-700e6)
sweeper.sweep.stop_freq(700e6)
sweeper.sweep.num_points(1001)
sweeper.sweep.mapping("linear")

# Note: The PSD feature supports hardware averages
sweeper.average.num_averages(1000)
sweeper.sweep.wait_after_integration(4e-6)
sweeper.average.mode("cyclic")

```

Next, we are going to configure the integration time for the power spectral density measurement. Note that the integration time determines the resolution bandwidth due to the windowing effect. Thus the integration time should be chosen to be similar or larger than the inverse frequency step size.

```python
freq_step = (sweeper.sweep.stop_freq() - sweeper.sweep.start_freq()) / (sweeper.sweep.num_points() - 1)
inverse_frequency_resolution = 1 / freq_step
print(f"Inverse frequency step size: {inverse_frequency_resolution:0.2e} s")
```

```python
sweeper.average.integration_time(1.0e-6)
```

```python
# Here we calculate the resolution bandwidth as the inverse of the integration time.
# This will be useful information to interpret the PSD result.
print(f"Resolution bandwidth: {1 / sweeper.average.integration_time():0.2e} Hz")
```

Enable the power spectral density (PSD) feature. When the PSD feature is enabled, the device computes the square of the absolute values of the integration results before averaging the results.

```python
sweeper.sweep.psd(True)

```

## Switch on the input channel

Here, we just switch on the input QA channel. Furthermore, we make sue that the output of the QA channel switched off, since typically the PSD feature is used to measure external signals.


```python
# Switch on the QA input channel
device.qachannels[main_channel].input.on(True)

# Make sure the output channel of the main QA channel is switched off
device.qachannels[main_channel].output.on(False)
```
## Run first PSD measurement

In this section, we run the first PSD meaurement.

This can be used to measure the PSD of an external signal and to characterize the input noise. In the next section, we will then proceed with generating a test signal.

```python
# Now run the actual PSD measurment
psd = sweeper.run()
```

```python
# Plot the results
sweeper.plot()
```

## Configure the test signal channel


Now, we configure a second channel of the SHFQA, or the first SG channel (SHFQC), in order to generate a test signal that can be used for demonstrating the power spectral density measurement.
To use this test signal, a cable needs to be used to connect the QA signal input to the signal output of the second QA channel (SHFQA) or the first SG channel (SHFQC), as defined by `test_signal_channel` below.

Of course, this section can be skipped entirely when measuring an external signal.

```python
test_signal_output_range = -25

if device.device_type.startswith("SHFQA"):
    # On the SHFQA, a second QA channel will be used to generate a test signal
    test_signal_channel = 1
    # We use the readout mode on the test signal source channel for generating the test signal
    device.qachannels[test_signal_channel].configure_channel(
        # Note: the center frequency should match with the main channel to simplify the analysis of the results
        center_frequency=qachannel_center_frequency,
        input_range=qachannel_power_in,  # Note: the input will not be used on the test source channel
        output_range=test_signal_output_range,
        mode=SHFQAChannelMode.READOUT,
    )
    # Turn the test signal output channel on
    device.qachannels[test_signal_channel].output.on(True)

elif device.device_type.startswith("SHFQC"):
    # On the SHFQC, we use the first SG channel to generate the test signal
    test_signal_channel = 0

    # We use the SG channel as the test signal source for generating the test signal
    device.sgchannels[test_signal_channel].configure_channel(
        center_frequency=qachannel_center_frequency,
        output_range=test_signal_output_range,
        enable=True,
        rf_path=True,
    )
    # Turn the test signal output channel on
    device.sgchannels[test_signal_channel].output.on(True)

else:
    raise ValueError("Unkonwn device type: {device.device_type}")
```

```python
# Generate an interesting test waveform
from zhinst.toolkit import Waveforms
import numpy as np
from scipy import signal
from zhinst.utils.shfqa import SHFQA_SAMPLING_FREQUENCY

# Modulate a Gaussian with complex sinusoidal
modulation_freq = 100e6
# Note: the waveform length must be shorter than the integration time,
# since otherwise the test signal might overlap with next integration window.
waveform_length = np.min(128, int(sweeper.average.integration_time() / SHFQA_SAMPLING_FREQUENCY))
time_axis = np.arange(waveform_length) / SHFQA_SAMPLING_FREQUENCY
test_signal = np.exp(1j * 2 * np.pi * modulation_freq * time_axis)
test_signal *= signal.gaussian(waveform_length, std=waveform_length/8)

# Upload waveform to the device
waveforms = Waveforms()
waveforms.assign_waveform(
    slot=0,
    wave1=test_signal,
)
```

```python
# Configure the AWG to generate the test channel
if device.device_type.startswith("SHFQA"):
    seqc_program = f"""
        while(1) {{
            waitDigTrigger(1);
            startQA(QA_GEN_0, 0x0, true, 0, 0x0);
        }}
    """
    device.qachannels[test_signal_channel].generator.load_sequencer_program(seqc_program)
    device.qachannels[test_signal_channel].generator.write_to_waveform_memory(waveforms)
    # Trigger the sequencer for the test signal via the sequencer on the main channel
    device.qachannels[test_signal_channel].generator.configure_sequencer_triggering(aux_trigger=f"chan{main_channel}seqtrig0")

elif device.device_type.startswith("SHFQC"):
    seqc_program = f"""
        wave w = placeholder({waveform_length});
        assignWaveIndex(1,2,w,1,2,w,0);
        while(1) {{
            waitDigTrigger(1);
            playWave(1,2,w,1,2,w);
    }}
    """
    elf_file, info = device.sgchannels[test_signal_channel].awg.compile_sequencer_program(seqc_program)
    waveforms.validate(elf_file)
    device.sgchannels[test_signal_channel].awg.elf.data(elf_file)
    device.sgchannels[test_signal_channel].awg.write_to_waveform_memory(waveforms)

    # Trigger the sequencer for the test signal via the sequencer on the main channel
    device.sgchannels[test_signal_channel].awg.auxtriggers[0].channel(f"chan{main_channel}seqtrig0")
else:
    raise ValueError("Unkonwn device type: {device.device_type}")
```

```python
# Define a function to enable the test signal later:
def set_test_signal_enable(enable: bool):
    if device.device_type.startswith("SHFQA"):
        device.qachannels[test_signal_channel].generator.enable(enable)
    elif device.device_type.startswith("SHFQC"):
        device.sgchannels[test_signal_channel].awg.enable(enable)
    else:
        raise ValueError("Unkonwn device type: {device.device_type}")
```

## Measure power spectral density


### PSD measurement (test signal switched off)


Here, we measure the power spectral density when the test signal is switched off.





```python
# Measure a PSD while the test signal is switched off
set_test_signal_enable(False)
psd_off = sweeper.run()

```

```python
# Use sweeper plotting function
sweeper.plot()

```

### PSD measurement (test signal switched on)


Now we perform a measurement of the PSD when the test signal is switched on.

```python
# Meausre the PSD with the test signal switched on
set_test_signal_enable(True)
psd_on = sweeper.run()

# Switch off the test signal generator again
set_test_signal_enable(False)
```

```python
# use sweeper plotting function
sweeper.plot()

```

# Analyze the results


First, we analyze the ratio between the "on" and "off" measurements to extract the exact spectral shape of the test signal by noise subtraction.

```python
import matplotlib.pyplot as plt

freq_axis_mhz = np.linspace(
    psd_on["properties"]["startfreq"],
    psd_on["properties"]["stopfreq"],
    psd_on["properties"]["numpoints"],
    endpoint=True) * 1e-6

plt.figure()
plt.plot(freq_axis_mhz, 10 * np.log10(psd_on["vector"].real / psd_off["vector"].real))
plt.xlabel("Offset Frequency [MHz]")
plt.ylabel("Ratio of PSD with test signal on/off [dB]")
plt.show()
```

Next, we are going to compute the theoretically expected power spectral density for the generated pulse

```python
# make sure the signal has the same length as the integration window
integration_length = int(SHFQA_SAMPLING_FREQUENCY * sweeper.average.integration_time())
if len(test_signal) < integration_length:
    # pad the test signal to the integration length
    test_signal_padded = np.pad(
        test_signal, (0, integration_length - len(test_signal)), mode="constant")
else:
    print(f"Warning: the waveform length ({len(test_signal)}) samples ",
    f"is longer than the integration length ({integration_length} samples).",
    "This condition will likely cause a mismatch between the calculated PSD and the actual PSD."
    )
    test_signal_padded = test_signal[:integration_length]

# scale test signal by calculated voltage range in units Volt, Root Mean Square (V_RMS)
input_impedance_ohm = 50
test_signal_padded *= np.sqrt(10.0**(test_signal_output_range
                               / 10) / 1e3 * input_impedance_ohm)

calculated_psd = (np.abs(np.fft.fft(test_signal_padded)) ** 2) / (SHFQA_SAMPLING_FREQUENCY * len(test_signal_padded))
calculated_psd_freqs = np.fft.fftfreq(len(calculated_psd), d=1/SHFQA_SAMPLING_FREQUENCY)

# shift frequencies so that negative frequencies come first (on the left)
calculated_psd = np.fft.fftshift(calculated_psd)
calculated_psd_freqs = np.fft.fftshift(calculated_psd_freqs)

```

```python
# Create an overlay plot of the measured and expected PSD
plt.figure()
plt.plot(freq_axis_mhz, psd_on["vector"].real, label="measured")
plt.plot(calculated_psd_freqs * 1e-6, calculated_psd, label="calculated", linestyle="dashed")
plt.xlabel("Offset Frequency [MHz]")
plt.ylabel(r"Power spectral density [${V_\mathrm{RMS}}^2 / \mathrm{Hz}$]")
plt.legend()
plt.show()

```

```python
# Plot the same as above in logarithmic (dBm / Hz) units
plt.figure()
plt.plot(freq_axis_mhz, 10*np.log10(psd_on["vector"].real * 1000 / 50), label="measured")
plt.plot(calculated_psd_freqs * 1e-6, 10*np.log10(calculated_psd * 1000 / 50), label="calculated", linestyle="dashed")
plt.xlabel("Offset Frequency [MHz]")
plt.ylabel("Power spectral density [dBm / Hz]")
plt.legend()
# Note: you might need to adjust the limits of the y-axis depending on the chosen input/output range!
plt.ylim([-145, -115])
plt.grid()
plt.show()

```

```python

```
