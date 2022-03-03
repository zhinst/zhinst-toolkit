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
    display_name: Python 3
    language: python
    name: python3
---

<!-- #region -->
# Resonator spectroscopy CW vs. Power


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
number_of_qubits = 2

qachannel_center_frequency = 7.1e9
qachannel_power_in = 5
qachannel_power_out = 0

max_amplitude_readout = 1 / number_of_qubits * 0.98

# Sweep Parameter
qubit_readout_frequencies = [125e6, 402e6, -570e6, -157.5e6, -352e6]
qubit_readout_widths = [20e6, 20e6, 20e6, 20e6, 20e6]
number_amplitude_values = 2
average_factor = 1e-6 # if set to 1, scales averages with amplitude
```

## Device configuration

```python
device.qachannels[0].configure_channel(
    center_frequency=qachannel_center_frequency,
    input_range=qachannel_power_in,
    output_range=qachannel_power_out,
    mode=SHFQAChannelMode.SPECTROSCOPY,
)
```

## Sweeper configuration

```python
# initiates sweeper parameters
sweeper = session.modules.shfqa_sweeper
sweeper.device(device)

sweeper.rf.center_freq(qachannel_center_frequency)
sweeper.rf.input_range(qachannel_power_in)
sweeper.rf.output_range(qachannel_power_out)

sweeper.sweep.start_freq(-700e6)
sweeper.sweep.stop_freq(700e6)
sweeper.sweep.num_points(1001)
sweeper.sweep.mapping("linear")
sweeper.sweep.oscillator_gain(max_amplitude_readout)
sweeper.sweep.mode(True)

sweeper.average.integration_time(1000e-6)
sweeper.average.num_averages(1)
sweeper.average.mode("cyclic")
```

## Measure each resonator with different powers

```python
import sys
import os
import numpy as np

resonator_spectrum_data = {"qubits": [[]] * number_of_qubits}
relative_amplitude_values = np.linspace(
    max_amplitude_readout / number_amplitude_values,
    max_amplitude_readout,
    number_amplitude_values,
)

device.qachannels[0].input.on(1)
device.qachannels[0].output.on(1)

print(f"sweep {number_of_qubits} qubits at {number_amplitude_values} amplitudes")

for qubit in range(number_of_qubits):
    sweeper.sweep.start_freq(
        qubit_readout_frequencies[qubit] - qubit_readout_widths[qubit]
    )
    sweeper.sweep.stop_freq(
        qubit_readout_frequencies[qubit] + qubit_readout_widths[qubit]
    )

    for i, amplitude in enumerate(relative_amplitude_values):
        sweeper.sweep.oscillator_gain(amplitude)
        sweeper.average.num_averages(int(np.ceil(average_factor * 1 / amplitude ** 2)))
        print(
            f"qubit: {qubit+1} amp: {amplitude:.5f} ({i+1}/{number_amplitude_values})",
            end="\r",
        )
        old_stdout = sys.stdout  # backup current stdout
        sys.stdout = open(os.devnull, "w")
        resonator_spectrum_data["qubits"][qubit].append(sweeper.run())
        sys.stdout = old_stdout  # reset old stdout

device.qachannels[0].input.on(0)
device.qachannels[0].output.on(0)

```

# Note to Tobias:
1. we had a problem here with the correct display of the data of the scans, somehow the axes did not align properly with the measurements -> could you crosscheck? if there is a simple way of cleaning up the plots, that would of course also be great
2. Above you introduced the function sweeper.sweep.mode -> this I find a bit unclear for a user, as it determines if the sequencer is used to sweep. use_sequencer -> in the sweeper API -> could we mirror this somehow in toolkit?
3. with the saving of the data, something is wrong. looks like that append(sweeper.run) acts on all (qubit)entries of resonator_spectrum_data



## Plot the data for each qubit

```python
resonator_spectrum_data['qubits'][0]==resonator_spectrum_data['qubits'][1]
```

```python
import matplotlib.pyplot as plt
from shfqc_helper import voltage_to_power_dBm

figsize=(24,10)
font_large=30
font_medium=20

num_points = sweeper.sweep.num_points()

for qubit in range(number_of_qubits):
    number_amplitude_values = np.size(relative_amplitude_values)
    x_data = np.zeros((number_amplitude_values, num_points))
    y_data = np.zeros((number_amplitude_values, num_points))
    z_data = np.zeros((number_amplitude_values, num_points), dtype=complex)
    slope_array = np.zeros((number_amplitude_values, num_points))

    for amp_ind, amplitude in enumerate(relative_amplitude_values):
        spec_path = resonator_spectrum_data["qubits"][qubit][amp_ind]
        spec_path_props = spec_path["properties"]

        x_data[amp_ind] = (
            np.linspace(
                spec_path_props["startfreq"],
                spec_path_props["stopfreq"],
                spec_path_props["numpoints"],
            )
            / 10 ** 6
        )
        y_data[amp_ind] = amplitude
        z_data[amp_ind] = spec_path["vector"]
        slope = 0.035
        slope_array[amp_ind] = slope * x_data[amp_ind]

    fig, axs = plt.subplots(1, 2, figsize=figsize)
    fig.suptitle(f"Qubit {qubit+1}", fontsize=font_large)
    color_amp = axs[0].scatter(
        x_data.flatten(),
        y_data.flatten(),
        s=20000,
        c=voltage_to_power_dBm(z_data.flatten()),
        marker="s",
    )
    axs[0].set_ylim([0, np.max(relative_amplitude_values)])
    axs[0].set_title("amplitude [dBm]", fontsize=font_medium)
    axs[0].set_xlabel("frequency [MHz]", fontsize=font_medium)
    axs[0].set_ylabel("rel. probe amplitude", fontsize=font_medium)
    axs[0].tick_params(axis="both", which="major", labelsize=font_medium)
    cbar = fig.colorbar(color_amp, ax=axs[0])
    cbar.ax.tick_params(labelsize=font_medium)

    color_phase = axs[1].scatter(
        x_data.flatten(),
        y_data.flatten(),
        s=20000,
        c=np.unwrap(np.angle(z_data)).flatten() + slope_array.flatten(),
        marker="s",
    )
    axs[1].set_ylim([0, np.max(relative_amplitude_values)])
    axs[1].set_title("phase [rad]", fontsize=font_medium)
    axs[1].set_xlabel("frequency [MHz]", fontsize=font_medium)
    axs[1].set_ylabel("rel. probe amplitude", fontsize=font_medium)
    axs[1].tick_params(axis="both", which="major", labelsize=font_medium)
    cbar = fig.colorbar(color_phase, ax=axs[1])
    cbar.ax.tick_params(labelsize=font_medium)

    plt.show()
```
