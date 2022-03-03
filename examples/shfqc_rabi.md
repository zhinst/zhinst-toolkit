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
# Pulsed Rabi Measurement - Determine Readout Angle and Pi-Pulse


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

## Device configuration

```python
import numpy as np
number_of_qubits = 4

qachannel_number = 0
qachannel_center_frequency = 7.1e9
qachannel_power_in = -50
qachannel_power_out = -30

max_amplitude_readout = 2.5 / number_of_qubits * 0.98

# configure inputs and outputs
device.qachannels[0].configure_channel(
    center_frequency=qachannel_center_frequency,
    input_range=qachannel_power_in,
    output_range=qachannel_power_out,
    mode=SHFQAChannelMode.READOUT,
)

sgchannel_number = list(range(number_of_qubits))
sgchannel_center_frequency = [4.7e9, 4.7e9, 3.2e9, 3.2e9]
sgchannel_power_out = [10] * number_of_qubits
sgchannel_trigger_input = 0

# configure sg channels
with device.set_transaction():
    device.qachannels[0].markers[0].source("channel0_sequencer_trigger0")
    device.qachannels[0].markers[1].source("channel0_sequencer_trigger0")
    device.qachannels[0].generator.auxtriggers[1].channel("channel0_trigger_input0")
    device.qachannels[0].triggers[0].level(0.1)
    for qubit in range(number_of_qubits):
        sg_channel = sgchannel_number[qubit]
        synth_channel = int(np.floor(sg_channel / 2)) + 1
        device.synthesizers[synth_channel].centerfreq(
            sgchannel_center_frequency[qubit]
        )
        device.sgchannels[sg_channel].output.range(sgchannel_power_out[qubit])
        device.sgchannels[sg_channel + 2].trigger.level(0.1)
        device.sgchannels[sg_channel].awg.auxtriggers[0].channel(
            sgchannel_trigger_input + 2
        )
        device.sgchannels[sg_channel].awg.auxtriggers[0].slope(1)
        device.sgchannels[sg_channel].marker.source("awg_trigger0")
```

## Setup SHFQC for the pulsed Rabi measurement

```python
# define parameters
qubit_drive_frequency=[299.260e6,275.990e6,-25e6,320e6,82e6]
num_steps_rabi_experiment = 100
num_averages_rabi_experiment = 2 ** 12
qubit_T1_time = [50e-6, 50e-6, 50e-6, 50e-6, 50e-6]
qubit_single_gate_time = [10e-9, 10e-9, 10e-9, 10e-9, 10e-9]
max_drive_strength = [1, 1, 1, 1, 1]
qubit_readout_frequencies=[407e6,130e6,-570e6,-157.5e6,-352e6]
readout_pulse_duration=  2e-6
qubit_readout_amplitudes = [max_amplitude_readout] * 5
wait_factor_in_T1 = 5
propagation_delay=226e-9
```

### Generate readout pulses and weights

```python
from shfqc_helper import generate_flat_top_gaussian
from zhinst.deviceutils.shfqa import SHFQA_SAMPLING_FREQUENCY
import numpy as np

# generate readout pulses and weights
readout_pulses = generate_flat_top_gaussian(
    frequencies=qubit_readout_frequencies,
    pulse_duration=readout_pulse_duration,
    rise_fall_time=5e-9,
    sampling_rate=SHFQA_SAMPLING_FREQUENCY,
    scaling=0.99,
)

weights = {}
rotation_angle=0
for waveform_slot, pulse in readout_pulses.items():
    weights[waveform_slot] = np.conj(pulse * np.exp(1j * rotation_angle))

for qubit in range(number_of_qubits):
    readout_pulses[qubit] = (
        readout_pulses[qubit] * qubit_readout_amplitudes[qubit]
    )

device.qachannels[0].generator.write_to_waveform_memory(readout_pulses)

# configure result logger and weighted integration
device.qachannels[0].readout.write_integration_weights(
    weights,
    # compensation for the delay between generator output and input of the integration unit
    integration_delay=propagation_delay,
)
```

### Configure readout channel

```python
from zhinst.toolkit import AveragingMode
pulse_startQA_string = "QA_GEN_0"
weight_startQA_string = "QA_INT_0"
for i in range(number_of_qubits - 1):
    pulse_startQA_string = pulse_startQA_string + f" | QA_GEN_{i+1}"
    weight_startQA_string = weight_startQA_string + f" | QA_INT_{i+1}"

# converts width of single qubit gate assuming its a gaussian to a good waveform length in samples
# assuming the optimal waveform length is 8 times the width of the gaussian
single_qubit_pulse_time_seqSamples = int(
    np.max(qubit_single_gate_time) * SHFQA_SAMPLING_FREQUENCY
)
single_qubit_pulse_time_samples = single_qubit_pulse_time_seqSamples * 8
readout_pulse_duration_samples = int(
    np.ceil(
        (readout_pulse_duration * SHFQA_SAMPLING_FREQUENCY + 10)
        / 16
    )
    * 16
)
time_to_next_experiment_seqSamples = int(
    np.max(qubit_T1_time)
    * wait_factor_in_T1
    * SHFQA_SAMPLING_FREQUENCY
    / 8
)

seqc_program_qa = f"""
waitDigTrigger(1); // wait for software trigger to start experiment
repeat({num_averages_rabi_experiment}) {{
    repeat({num_steps_rabi_experiment}) {{
        // Trigger control channels to play pulse
        setTrigger(1);
        wait(2);
        setTrigger(0);
        //wait('triggerdelay') // reference point


        // wait until control sequence finished
        wait({single_qubit_pulse_time_seqSamples});

        //start readout
        playZero({readout_pulse_duration_samples});
        startQA({pulse_startQA_string}, {weight_startQA_string}, true, 0, 0x0);

        //wait for qubit decay
        wait({time_to_next_experiment_seqSamples});
    }}
}}

"""
device.qachannels[0].generator.load_sequencer_program(seqc_program_qa)

singleShot = True
if singleShot:
    device.qachannels[0].readout.configure_result_logger(
        result_source="integration",
        result_length=num_steps_rabi_experiment * num_averages_rabi_experiment,
        num_averages=1,
        averaging_mode=AveragingMode.CYCLIC,
    )
else:
    device.qachannels[0].readout.configure_result_logger(
        result_source="integration",
        result_length=num_steps_rabi_experiment,
        num_averages=num_averages_rabi_experiment,
        averaging_mode=AveragingMode.CYCLIC,
    )
device.qachannels[0].readout.run()
device.qachannels[0].generator.enable_sequencer(single=True)
```

### Configure control channels

```python
import inspect
from zhinst.toolkit import CommandTable

# Predefine command table
ct = CommandTable(device.sgchannels[0].awg.commandtable.load_validation_schema())
ct.table[0].waveform.index = 0
ct.table[0].amplitude00.value = 0.0
ct.table[0].amplitude01.value = -0.0
ct.table[0].amplitude10.value = 0.0
ct.table[0].amplitude11.value = 0.0
ct.table[1].waveform.index = 0
ct.table[1].amplitude00.increment = True
ct.table[1].amplitude01.increment = True
ct.table[1].amplitude10.increment = True
ct.table[1].amplitude11.increment = True

for qubit in range(number_of_qubits):
    with device.set_transaction():
        device.sgchannels[sgchannel_number[qubit]].sines[0].i.enable(0)
        device.sgchannels[sgchannel_number[qubit]].sines[0].q.enable(0)
        device.sgchannels[sgchannel_number[qubit]].awg.modulation.enable(1)
        device.sgchannels[sgchannel_number[qubit]].oscs[0].freq(
            qubit_drive_frequency[qubit]
        )

    # Upload waveform
    seqc = inspect.cleandoc(
        f"""
    // Define a single waveform
    wave rabi_pulse=gauss({single_qubit_pulse_time_samples}, 1, {single_qubit_pulse_time_samples/2}, {qubit_single_gate_time[qubit]*SHFQA_SAMPLING_FREQUENCY});

    // Assign a dual channel waveform to wave table entry
    assignWaveIndex(1,2,rabi_pulse, 1,2,rabi_pulse, 0);
    resetOscPhase();
    repeat ({num_averages_rabi_experiment}) {{
        waitDigTrigger(1);
        executeTableEntry(0);
        repeat ({num_steps_rabi_experiment}-1) {{
            waitDigTrigger(1);
            executeTableEntry(1);
        }}
    }}
    """
    )

    device.sgchannels[sgchannel_number[qubit]].awg.load_sequencer_program(seqc)

    # update command table
    increment_value = max_drive_strength[qubit] / (
        num_steps_rabi_experiment - 1
    )
    ct.table[1].amplitude00.value = increment_value
    ct.table[1].amplitude01.value = -increment_value
    ct.table[1].amplitude10.value = increment_value
    ct.table[1].amplitude11.value = increment_value

    device.sgchannels[sgchannel_number[qubit]].awg.commandtable.upload_to_device(ct)
```

## Measurements

```python
from shfqc_helper import run_experiment

device.qachannels[0].readout.configure_result_logger(
    result_source="integration",
    result_length=num_steps_rabi_experiment,
    num_averages=num_averages_rabi_experiment,
    averaging_mode=AveragingMode.CYCLIC,
)

readout_results = run_experiment(device, sgchannel_number, number_of_qubits, reenable=True)
```

## Results

```python
import matplotlib.pyplot as plt
import numpy as np
import pickle

saveloc="PSIMeasurements/Rabi1"

with open(saveloc+".pkl", "wb") as f:
    pickle.dump(readout_results, f)

interactive = 1
if interactive ==1:
    %matplotlib widget
    figsize=(12,5)
    font_large=15
    font_medium=10
else:
    %matplotlib inline
    figsize=(24,10)
    font_large=30
    font_medium=20

for qubit in range(number_of_qubits):
    x_axis = np.linspace(
        0, max_drive_strength[qubit], num_steps_rabi_experiment
    )
    fig3, axs = plt.subplots(1, 2, figsize=figsize)
    fig3.suptitle(f"Qubit {qubit}", fontsize=font_large)
    axs[0].plot(x_axis, np.real(readout_results[qubit] - readout_results[qubit][0]))
    axs[0].set_title("I quadrature [A.U.]", fontsize=font_medium)
    axs[0].set_xlabel("pulse amplitude [A.U.]", fontsize=font_medium)
    axs[0].set_ylabel("quadrature [A.U.]", fontsize=font_medium)
    axs[0].tick_params(axis="both", which="major", labelsize=font_medium)

    axs[1].plot(x_axis, np.imag(readout_results[qubit] - readout_results[qubit][0]))
    axs[1].set_title("Q quadrature [A.U.]", fontsize=font_medium)
    axs[1].set_xlabel("pulse amplitude [A.U.]", fontsize=font_medium)
    axs[1].set_ylabel("quadrature [A.U.]", fontsize=font_medium)
    axs[1].tick_params(axis="both", which="major", labelsize=font_medium)

    plt.savefig(saveloc + f"{qubit}.png")
    plt.show()
```

## Rotate integration weights

```python
qubit_readout_rotation = [
    -0.95 * np.pi,
    0.85 * np.pi,
    0.85 * np.pi,
    0.85 * np.pi,
    0.85 * np.pi,
]

# rotate weights according to readout parameter settings
weightsrot = {
    i: np.multiply(weights[i], np.exp(1j * qubit_readout_rotation[i]))
    for i in range(number_of_qubits)
}

device.qachannels[0].readout.write_integration_weights(
    weightsrot,
    # compensation for the delay between generator output and input of the integration unit
    integration_delay=propagation_delay,
)


device.qachannels[0].readout.configure_result_logger(
    result_source="integration",
    result_length=num_steps_rabi_experiment,
    num_averages=num_averages_rabi_experiment,
    averaging_mode=AveragingMode.CYCLIC,
)
```

## Measurments

```python
readout_results_rotated = run_experiment(device, sgchannel_number, number_of_qubits, reenable=True)
```

## Results

```python
import matplotlib.pyplot as plt
import numpy as np
import pickle

saveloc="PSIMeasurements/Rabi2"

with open(saveloc+".pkl", "wb") as f:
    pickle.dump(readout_results_rotated, f)

interactive = 1
if interactive ==1:
    %matplotlib widget
    figsize=(12,5)
    font_large=15
    font_medium=10
else:
    %matplotlib inline
    figsize=(24,10)
    font_large=30
    font_medium=20

# plot results
for qubit in range(number_of_qubits):
    x_axis = np.linspace(
        0, max_drive_strength[qubit], num_steps_rabi_experiment
    )

    fig3, axs = plt.subplots(1, 2, figsize=figsize)
    fig3.suptitle(f"Qubit {qubit}", fontsize=font_large)
    axs[0].plot(x_axis, np.real(readout_results_rotated[qubit] - readout_results_rotated[qubit][0]))
    axs[0].set_title("I quadrature [A.U.]", fontsize=font_medium)
    axs[0].set_xlabel("pulse amplitude [A.U.]", fontsize=font_medium)
    axs[0].set_ylabel("quadrature [A.U.]", fontsize=font_medium)
    axs[0].tick_params(axis="both", which="major", labelsize=font_medium)

    axs[1].plot(x_axis, np.imag(readout_results_rotated[qubit] - readout_results_rotated[qubit][0]))
    axs[1].set_title("Q quadrature [A.U.]", fontsize=font_medium)
    axs[1].set_xlabel("pulse amplitude [A.U.]", fontsize=font_medium)
    axs[1].set_ylabel("quadrature [A.U.]", fontsize=font_medium)
    axs[1].tick_params(axis="both", which="major", labelsize=font_medium)

    plt.savefig(saveloc + f"{qubit}.png")
    plt.show()
```

## Fit data

```python
from shfqc_helper import amplitude_rabi, fit_data
qubit_pi_amplitude = [None]*number_of_qubits
qubit_pi_2_amplitude = [None]*number_of_qubits
for qubit in range(number_of_qubits):
    amp_axis=np.linspace(0,max_drive_strength[qubit],num_steps_rabi_experiment)
    y_data = np.abs(readout_results[qubit]-readout_results[qubit][0])
    if False:
        y_data = amplitude_rabi(amp_axis, 45 , 5)
        noise = 1*np.random.normal(size=y_data.size)
        y_data += noise
    pars, stdevs=fit_data(amp_axis,y_data,amplitude_rabi,[30 , 10],1,figsize=figsize,font=font_medium,qubit=qubit,x_label='rel. qubit drive amplitude',y_label='amplitude [A.U.]',saveloc=f'PSIMeasurements/RabiFit{qubit}')
    qubit_pi_amplitude[qubit]= 2*np.pi/pars[0]
    qubit_pi_2_amplitude[qubit]= np.pi/pars[0]

    print('qubit',qubit,': pi-amp. =', qubit_pi_amplitude[qubit] ,'\n'
          '          pi/2-amp. =', qubit_pi_2_amplitude[qubit])
```
