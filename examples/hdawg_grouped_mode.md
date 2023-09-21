---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.14.7
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# Zurich Instruments LabOne Python API Example
## Control the HDAWG in grouped mode

Demonstrate how to connect to a Zurich Instruments HDAWG in grouped mode. The grouped mode allows to control multiple 
AWG outputs with a single sequencer program.

Requirements:
* LabOne Version >= 23.06
* Instruments:
    1 x HDAWG Instrument

---

```python
import numpy as np
import time

import zhinst.toolkit as tk
```

Set up the connection. The connection is always through a session to a
Data Server. The Data Server then connects to the device.

The LabOne Data Server needs to run within the network, either on localhost when
starting LabOne on your local computer or a remote server.

```python
# Device serial number available on its rear panel.
device_id = "DEVXXXX"

# Connect to the dataserver
session = tk.Session("localhost")

device = session.connect_device(device_id)

# reset to default values
device.factory_reset()

# check if firmware is compatible
try:
    device.check_compatibility()
except tk.exceptions.ToolkitError as e:
    print(f"{e}\nPlease update the firmware on your device.")
```

### Basic configuration
In this example the device is configured to control groups of 4 outputs with a single sequencer program (channel grouping 1). It is also possible to control groups of 2 outputs (channel grouping 0) or 8 outputs (channel grouping 2).

After specifying the grouping mode, specify which group to use and set the output gains for each AWG core in the group. Then set the output range for each channel in the group and switch the channels on.

```python
grouping = 1        # Channel grouping 2x4
awg_group = 0       # AWG group
output_range = 1.0  # Output range [V]

awg_cores_i = awg_group * 2**grouping + np.arange(2**grouping)        # AWG cores
channels_i = awg_group * 2**(grouping+1) + np.arange(2**(grouping+1)) # Output channels

awg_cores = [device.awgs[awg_core] for awg_core in awg_cores_i]
channels = [device.sigouts[channel] for channel in channels_i]

# Per-core settings
with device.set_transaction():
    
    # Grouping mode
    device.system.awg.channelgrouping(grouping)
    
    for awg_core in awg_cores:
        awg_core.outputs[0].gains[0](1.0)         # Set the output gains matrix to identity
        awg_core.outputs[0].gains[1](0.0)
        awg_core.outputs[1].gains[0](0.0)
        awg_core.outputs[1].gains[1](1.0)
        awg_core.outputs[0].modulation.mode(0)    # Turn off modulation mode
        awg_core.outputs[1].modulation.mode(0)

    # Per-channel settings
    for channel in channels:
        channel.range(output_range)     # Select the output range
        channel.on(True)                # Turn on the outputs. Should be the last setting
```

### AWG sequencer program
Define an AWG program as a string stored in the variable `awg_program`, equivalent to what would be entered in the Sequence Editor window in the graphical UI. Differently to a self-contained program, this example refers to a command table by the instruction `executeTableEntry`, and to placeholder waveforms `p1`, `p2`, `p3`, `p4` by the instruction `placeholder`. Both the command table and the waveform data for the placeholders need to be uploaded separately before this sequence program can be run.

After defining the sequencer program, this must be compiled before being uploaded. The function `load_sequencer_program` of `zhinst-toolkit`, which is the preferred tool for compiling AWG programs, does not support working with the grouped mode. For this reason, in this example the compilation must be done using the LabOne module `awgModule`.

```python
awg_program = tk.Sequence()
wfm_index = 0
wfm_length = 1024
awg_program.constants['wfm_index'] = wfm_index
awg_program.constants['wfm_length'] = wfm_length

awg_program.code = """
// Define placeholder with 1024 samples:
wave p1 = placeholder(wfm_length);
wave p2 = placeholder(wfm_length);
wave p3 = placeholder(wfm_length);
wave p4 = placeholder(wfm_length);

// Assign an index to the placeholder waveform
assignWaveIndex(1,p1, 2,p2, wfm_index);
assignWaveIndex(3,p3, 4,p4, wfm_index);

while(true) {
  executeTableEntry(0);
}
"""

# Conver to a string
awg_program = str(awg_program)
```

Compile and upload the AWG program to the device using the AWG Module.

```python
awgModule = session.modules.awg
awgModule.device(device.serial)
awgModule.index(awg_group)
awgModule.sequencertype('auto-detect')
awgModule.execute()

awgModule.compiler.sourcestring(str(awg_program))
```

Check that the sequencer program was compiled and uploaded correctly. This is not mandatory, but only to ensure that the script can continue with the next steps.

```python
# Wait until compilation is done
timeout = 10  # seconds
start = time.time()
compiler_status = awgModule.compiler.status()
while compiler_status == -1:
    if time.time() - start >= timeout:
        raise TimeoutError("Program compilation timed out")
    time.sleep(0.01)
    compiler_status = awgModule.compiler.status()

compiler_status_string = awgModule.compiler.statusstring()
if compiler_status == 0:
    print(
        "Compilation successful with no warnings, will upload the program to the instrument."
    )
if compiler_status == 1:
    raise RuntimeError(
        f"Error during sequencer compilation: {compiler_status_string:s}"
    )
if compiler_status == 2:
    print(f"Warning during sequencer compilation:  {compiler_status_string:s}")

# Wait until the sequence is correctly uploaded
start = time.time()
for awg_core in awg_cores:
    # Check the ready status for each core
    while awg_core.ready() == 0:
        # Timeout if all the cores doesn't report ready in time
        if time.time() - start >= timeout:
            raise TimeoutError(f"Sequence not uploaded within {timeout:.1f}s.")
        time.sleep(0.01)

print("Sequence successfully uploaded.")
```

### Command Table definition and upload

The waveforms are played by a command table, whose structure must conform to a defined schema. The schema can be read from the device. This example validates the command table against the schema before uploading it.


Read the schema from the device.

```python
# Creation of the command table
schema = device.awgs[0].commandtable.load_validation_schema()
ct1 = tk.CommandTable(schema)
ct2 = tk.CommandTable(schema)

print(f"The device is using the commandtable schema version {schema['version']}")
```

Define two command tables and automatically validate them against the schema.

```python
# First command table
ct1.table[0].waveform.index = wfm_index
ct1.table[0].amplitude0.value = 1.0
ct1.table[0].amplitude1.value = 1.0
# Second command table
ct2.table[0].waveform.index = wfm_index
ct2.table[0].amplitude0.value = 0.5
ct2.table[0].amplitude1.value = -1.0

cts = [ct1, ct2]
```

Upload the two command tables to the two AWG cores and check if the upload ends successfully.

```python
for ct, awg_core in zip(cts, awg_cores):
    awg_core.commandtable.upload_to_device(ct)

print("Command tables upload successful")
```

### Waveform upload

Replace the placeholder waveform with a drag pulse (I quadrature is a gaussian and Q quadrature is the derivative of I). The waveform data is uploaded to the index `wfm_index`, which must be the same specified by
the `assignWaveIndex` sequencer instruction.


Define the waveforms.

```python
x_array = np.linspace(-wfm_length//2, wfm_length//2, wfm_length)
sigma = wfm_length//8

waveforms = tk.Waveforms()

# Define the waveforms as numpy arrays
wave_ch0 = np.exp(-np.power(x_array, 2.0) / (2 * np.power(sigma, 2.0)))
wave_ch1 = -x_array/sigma**2 * wave_ch0

waveforms[0] = (wave_ch0, wave_ch1)
```

Upload the native waveforms to the device.

```python
with device.set_transaction():
    for awg_core in awg_cores:
        awg_core.write_to_waveform_memory(waveforms)

print("Waveforms upload successful")
```

### Enable the AWG 
This is the preferred method of using the AWG: run in single mode. Continuous waveform playback
is best achieved by using an infinite loop (e.g., `while (true)`) in the sequencer program.

Note that it is not necessary to enable all the AWG cores manually: by enabling one core, all the other are automatically enabled by the device. For this reason in this example only the first AWG core is enabled.

```python
with device.set_transaction():
    awg_cores[0].single(True)
    awg_cores[0].enable(True)
```
