---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.15.2
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# AWG Sequence Programming

The Arbitrary Waveform Generator functionality is realized using field-programmable
gate array (FPGA) technology and is available on multiple instruments types, like
the HDAWG or the SHFSG. Users can operate the AWG through a program called
sequencer code, it defines which waveforms are played and in which order. The
syntax of the LabOne AWG Sequencer programming language is based on C, but with
a few simplifications.

The user manuals for each device, that has a AWG available, provides detailed
explanation of all available commands and syntax.

LabOne provides the AWG module to compile and upload a sequencer program to the
device. In zhinst-toolkit this module is also available. In addition the devices
with AWG support also have helper function directly implemented in the node tree.

The functionality explained in the following example are valid for all devices
and are available behind the ``awg`` node.

Connect devices and access the ``awg`` node.

```python
# Load the LabOne API and other necessary packages
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")

AWG_CORE = 0
```

```python
if device.device_type.startswith('HDAWG'):
    awg_node = device.awgs[AWG_CORE]
elif device.device_type.startswith('SHFSG') or device.device_type.startswith('SHFQC'):
    awg_node = device.sgchannels[AWG_CORE].awg
```

## Compile and Upload Sequencer Program

The Sequencer program can be uploaded as string.

```python
SEQUENCER_CODE = """\
// Waveform paramaters
const WFM_LEN = 1008;
const GAUSS_CENTER = WFM_LEN/2;
const SIGMA = WFM_LEN/8;

// Define waveforms
wave w0_1 = gauss(WFM_LEN, 1.0, GAUSS_CENTER, SIGMA) + marker(128, 1);
wave w0_2 = drag(WFM_LEN, 1.0, GAUSS_CENTER, SIGMA);
wave w1_1 = gauss(WFM_LEN, 0.5, GAUSS_CENTER, SIGMA);
wave w1_2 = drag(WFM_LEN, 0.5, GAUSS_CENTER, SIGMA);

// Assign waveforms to an index in the waveform memory
assignWaveIndex(1,2, w0_1, 1,2, w0_2, 0);
assignWaveIndex(1,2, w1_1, 1,2, w1_2, 2);

// Play wave 1
playWave(1,2, w0_1, 1,2, w0_2);
// Play wave 2
playWave(1,2, w1_1, 1,2, w1_2);

"""

awg_node.load_sequencer_program(SEQUENCER_CODE)
```

```python
awg_node.enable_sequencer(single=True)
awg_node.wait_done()
```

**Warning**

The HDAWG can be programmed with the function `load_sequencer_program` only when in 4x2 or 2x2 mode. Other grouped modes (like 1x8, 2x4 or 1x4) should use the AWG module. See [hdawg_grouped_mode](hdawg_grouped_mode.md) for more details.


### Sequencer Class
zhinst-toolkit also offers a class `Sequence` representing a LabOne Sequence.
This class enables a compact representation of a sequence for a Zurich 
Instruments device. Although a sequencer code can be represented by a
simple string this class offers the following advantages:

    * Define a constants dictionary. The constants will be added
        automatically to the top of the resulting sequencer code and helps
        to prevent the use of fstrings (which require the escaping of {})
    * Link Waveforms to the sequence. This adds the waveform placeholder
        definitions to the top of the resulting sequencer code.
        (see the Waveform section below)

> Note:
>
> This class is only for convenience. The same functionality can be 
> achieved with a simple string.

```python
from zhinst.toolkit import Sequence

seq = Sequence()
seq.code = """\
// Hello World
repeat(5)
...
"""
seq.constants["PULSE_WIDTH"] = 10e-9 #ns
print(seq)
```

<!-- #region -->
## Waveform

The waveform must be first defined in the sequence, either as placeholder (like
in the sequencer code above) or as completely defined waveform with valid
samples. In the first case, the compiler will only allocate the required memory
and the waveform content is loaded later. The waveform definition must specify
the length and eventual presence of markers. This should be respected later when
the actual waveform is loaded.

In our case 2 waveforms have been defined. One has been assigned to index 0 and
the other one two index 2.


The waveform data can be uploaded directly in the native AWG waveform format
through its respective node (``/.../awgs/n/wavforms/wave/m``) which is also
accessible through zhinst-toolkit. For more information on the native AWG waveform
format take a look at the awg section in the
[labone user manuals](http://docs.zhinst.com/labone_programming_manual/awg_module.html).
zhinst-toolkit itself offers a second, more user friendly approach through the class
called ``Waveforms``.

The ``Waveform`` class is a mutable mapping, meaning it behaves similar to a
Python dictionary. The key defines the waveform index and the value is the waveform
data provided as a tuple. The waveform data consists of the following elements:

* wave 1 (numpy array between -1 and 1)
* wave 2 (numpy array between -1 and 1)
* markers (optional numpy array)

(wave 1 can be a complex array in which case the imaginary part will be treated
as wave 2)

The conversion to the native AWG waveform format (interleaved waves and markers
as uint16) is handled by the ``Waveform`` class directly.
<!-- #endregion -->

```python
import numpy as np
from zhinst.toolkit import Waveforms

waveforms = Waveforms()
# Waveform at index 0 with markers
waveforms[0] = (0.5*np.ones(1008), -0.2*np.ones(1008), np.ones(1008))
# Waveform at index 2 without markers
waveforms[2] = (np.random.rand(1008), np.random.rand(1008))

awg_node.write_to_waveform_memory(waveforms)
```

> Note:
>
> The waveform data can also be assigned via the helper function
> ``assign_waveform`` which converts the data into the same tuple
> as used above. Similar ``assign_native_awg_waveform`` can be used to
> assign already to a single native AWG format array converted waveform data to
> an index.


The same way one can upload the waveforms through a simple function one can also
download the waveforms from the device

```python
waveforms_device = awg_node.read_from_waveform_memory()
waveforms_device[0]
```

### Automatic sequencer code generation
As already discussed the waveforms must be defined in the sequencer program before they
can be uploaded to the device. In addition to convert the assigned waveforms to the 
native AWG format the `Waveform` class can also generate a sequencer code snippet
that defineds the waveforms present in the `Waveform` object.

```python
print(waveforms.get_sequence_snippet())
```

Additional meta information can be added to each waveform to customize the 
snippet output. The following meta information are supported:
* name: The name of the waveform. If specified, the placeholder will be assigned to
    a variable that can be in the sequencer program.
* output: Output configuration for the waveform.

```python
from zhinst.toolkit.waveform import Wave, OutputType
waveforms = Waveforms()
waveforms[1] = (
    Wave(0.5 * np.ones(1008), name= "w1", output= OutputType.OUT1 | OutputType.OUT2),
    Wave(-0.5 * np.ones(1008), name= "w2", output= OutputType.OUT1 | OutputType.OUT2),
    (1 << 0 | 1 << 1 | 1 << 2 | 1 << 3) * np.ones(1008),
)
waveforms.assign_waveform(2,
    Wave(np.ones(1008), name= "w3", output= OutputType.OUT2),
    Wave(-np.ones(1008), name= "w4", output= OutputType.OUT2),
    (1 << 1 | 1 << 3) * np.ones(1008),
)
waveforms[0] = (0.2 * np.ones(1008), -0.2 * np.ones(1008))
waveforms[0][0].name = "test1"

print(waveforms.get_sequence_snippet())
```

The `Waveforms` object can also be added to a `Sequence` object. This allows a 
a more structured code and prevents uploading the wrong waveforms. It also allows
an easy declaration of the waveforms in the sequencer code since the above
explained code snippet is automatically added to the sequencer code (can be 
disabled)

```python
seq =  Sequence("""\
// Play wave 1
playWave(1,2, w0_1, 1,2, w0_2);
// Play wave 2
playWave(1,2, w1_1, 1,2, w1_2);
""")

seq.waveforms = Waveforms()
seq.waveforms[0] = (
    Wave(0.5 * np.ones(1008), name= "w0_1", output= OutputType.OUT1 | OutputType.OUT2),
    Wave(-0.5 * np.ones(1008), name= "w0_2", output= OutputType.OUT1 | OutputType.OUT2),
    (1 << 0 | 1 << 1 | 1 << 2 | 1 << 3) * np.ones(1008),
)
seq.waveforms.assign_waveform(2,
    Wave(np.ones(1008), name= "w1_1", output= OutputType.OUT1 | OutputType.OUT2),
    Wave(-np.ones(1008), name= "w1_2", output= OutputType.OUT1 | OutputType.OUT2),
    (1 << 1 | 1 << 3) * np.ones(1008),
)

print(seq)
```

### Waveform validation
The waveform definitions must match the assignment in the sequencer code. To 
validate if a waveform matches a sequencer code the waveform class has a validation
function. 

Please note that it is not mandatory to call the validation function before 
uploading. But especially when debugging or playing around with the waveforms
it can be helpful.

The validation either takes the compiled elf file or the waveform informations
from the device (only if the sequencer code is already uploaded).

```python
waveforms = awg_node.read_from_waveform_memory()
elf,_ = awg_node.compile_sequencer_program(SEQUENCER_CODE)

waveforms.validate(elf)
waveforms.validate(awg_node.waveform.descriptors())
```

## Command Table

The command table allows the sequencer to group waveform playback instructions
with other timing-critical phase and amplitude setting commands in a single
instruction within one clock cycle of 3.33 ns. The command table is a unit
separate from the sequencer and waveform memory. Both the phase and the amplitude
can be set in absolute and in incremental mode. Even when not using digital
modulation or amplitude settings, working with the command table has the
advantage of being more efficient in sequencer instruction memory compared to
standard sequencing. Starting a waveform playback with the command table always
requires just a single clock cycle, as opposed to 2 or 3 when using a playWave
instruction.

For more information on the usage and advantages of the command table reference
to the [user manuals](https://docs.zhinst.com/hdawg_user_manual/tutorial_command_table.html#umhd.tutorials.ct.introduction).
Note that the command table is not supported on all devices that have an AWG.

The command tables is specified in the JSON format and need to conform to a device
specific schema. The user manuals explain in detail how the command table is
structured and used. Similar to the Waveforms zhinst-toolkit offers a helper class
for the command table usage called ``CommandTable``.

> Note:
>
> Since the command table structure is defined in a JSON schema the ``CommandTable``
> class requires this json schema as well. Either one stores a copy of it locally or
> it can be accessed in zhinst-toolkit through the function ``load_validation_schema``

```python
# Create a CommandTable instance  by using the schema
from zhinst.toolkit import CommandTable

ct_schema = awg_node.commandtable.load_validation_schema()
ct = CommandTable(ct_schema)
```

```python
# Alternately, load the existing command table from the device
ct = awg_node.commandtable.load_from_device()
```

The ``CommandTable`` class creates a pythonic approach of creating a command table
that is similar to the node tree usage in zhinst-toolkit. Elements can be accessed
either by value or by attribute.

Autocompletion is also available as well as on the fly validation.

```python
dir(ct.table[0])
```

```python
ct.table[0].waveform.info()
```

```python
ct.table[0].waveform.info("index")
```

```python
ct.table[0].waveform.index = 0
ct.table[0].waveform.index
```

```python
from zhinst.toolkit.exceptions import ValidationError
try:
    ct.table[0].waveform.index = -1
except ValidationError as err:
    print(err)
```

Each change to the command table will be validated on the fly. In addition
the moment it gets converted the complete structure is validated.

```python
ct.clear()
try:
    ct.table[0].waveform.index = 2
    ct.as_dict()
except ValidationError as err:
    print(err)
```

Once the command table is finished the upload to the device is taken care of
by zhinst-toolkit

```python
ct.clear()

if device.device_type.startswith('HDAWG'):
    ct.table[0].waveform.index = 0
    ct.table[0].amplitude0.value = 0.0
    ct.table[0].amplitude0.increment = False
    ct.table[0].amplitude1.value = 0.0
    ct.table[0].amplitude1.increment = False

    ct.table[1].waveform.index = 0
    ct.table[1].amplitude0.value = 0.007
    ct.table[1].amplitude0.increment = True
    ct.table[1].amplitude1.value = -0.007
    ct.table[1].amplitude1.increment = True

elif device.device_type.startswith('SHFSG') or device.device_type.startswith('SHFQC'):
    ct.table[0].waveform.index = 0
    ct.table[0].amplitude00.value = 0.0
    ct.table[0].amplitude01.value = 0.0
    ct.table[0].amplitude10.value = 0.0
    ct.table[0].amplitude11.value = 0.0
    ct.table[0].amplitude00.increment = False
    ct.table[0].amplitude01.increment = False
    ct.table[0].amplitude10.increment = False
    ct.table[0].amplitude11.increment = False

    ct.table[1].waveform.index = 0
    ct.table[1].amplitude00.value = 0.07
    ct.table[1].amplitude01.value = -0.07
    ct.table[1].amplitude10.value = 0.07
    ct.table[1].amplitude11.value = 0.07
    ct.table[1].amplitude00.increment = True
    ct.table[1].amplitude01.increment = True
    ct.table[1].amplitude10.increment = True
    ct.table[1].amplitude11.increment = True

awg_node.commandtable.upload_to_device(ct)
```

<!-- #region -->
### Command table active validation
Command table validates the given arguments on the fly by default. The feature has overhead and can
be turned off to improve production code runtimes. Disabling it is good especially when creating a large
command table with multiple table indexes. In any case, the command table is always validated upon upload and the instruments itself checks again errors.

On the fly validation can be disabled by:
```python
ct.active_validation = False
```
<!-- #endregion -->

## Performance optimzation
Often the limiting factor for an experiment is the delay of the device communication.
If this is the case it is best trying to reduce the number of uploads. 
For the AWG core this means uploading everything in a single transaction.

> **Warning**:
> The order is to some extend crutial. Meaning the sequencer code needs to be at the
> beginning and the enable call at the end.

> **Note**:
> The bundling of the upload is not limited to a single awg core but can combine
> multiple cores.

> **Note**:
> It is also possible to do the transaction on a session level so that it applies for
> multiple instruments.

```python
seq = Sequence()
seq.code = """\
// Simple playback loop
while(true) {
    executeTableEntry(0);
}
"""

seq.waveforms = Waveforms()
seq.waveforms[10] = (np.zeros(1024), np.ones(1024))

ct = CommandTable(ct_schema)
ct.active_validation = False

ct.table[0].waveform.index = 10

with device.set_transaction():
    awg_node.load_sequencer_program(seq)
    awg_node.write_to_waveform_memory(seq.waveforms)
    awg_node.commandtable.upload_to_device(ct)
    awg_node.enable(True)
```

Optionally, the sequence can be compiled and the resulting ELF uploaded manually

```python
elf,_ = awg_node.compile_sequencer_program(seq)
with device.set_transaction():
    awg_node.elf.data(elf)
    awg_node.write_to_waveform_memory(seq.waveforms)
    awg_node.commandtable.upload_to_device(ct)
    awg_node.enable(True)
```

## Multi-core programming

So far, all the example referred to a single sequencer, but the signal generators have multiple output channels. To control all of them we must program all the relative sequencers.

This could be done just by sequentially loading the relative sequences:

```python
# Get a list of all the AWG cores on a device

if device.device_type.startswith('HDAWG'):
    awg_nodes = list(device.awgs)
elif device.device_type.startswith('SHFSG') or device.device_type.startswith('SHFQC'):
    awg_nodes = [sgchannel.awg for sgchannel in device.sgchannels]
```

```python
# Generate a list of test sequences

from textwrap import dedent
num_cores = len(awg_nodes)
sequences = [
    dedent(f"""\
    // Core {i:d} sequence
    waitDigTrigger(1);  //Wait for a trigger to syncronize all the cores
    playWave(ramp(1024, 0, {(i+1)/num_cores:f}));
    """)
    for i in range(num_cores)
]
```

```python
# Sequentially compile and upload all the sequences

from zhinst.core.errors import CoreError
with session.set_transaction():
    for index, (awg_node, sequence) in enumerate(zip(awg_nodes, sequences)):
        try:
            _ = awg_node.load_sequencer_program(sequence)
        except CoreError as e:
            print("Compilation error on core", index, e)
            break
```

If the sequences are particularly long, it worth to compile them in parallel. The `ThreadPollExecutor` will use a number of threads depending on the CPU core count. Differently from generic Python code, the seqc compiler can use multiple cores at the same time, if used correctly.

Please note that in such case the `set_transaction` is mandatory. The LabOne API is not thread safe, and the transaction ensures that the sequences are sequentially uploaded to the device(s).

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with session.set_transaction(), ThreadPoolExecutor() as executor:
    #Compile and upload all the sequences
    # Get and store a future to verify the compilation once is done
    futures = {}
    for index, (awg_node, sequence) in enumerate(zip(awg_nodes, sequences)):
        future = executor.submit(awg_node.load_sequencer_program, sequence)
        futures[future] = index

    #Checks the errors
    # Iterate over all futures to verify the compilation
    for future in as_completed(futures):
        index = futures[future]
        try:
            _ = future.result()
        except CoreError as e:
            print("Compilation error on core", index, e)
```

Here a more complex example, with "heavy" sequences and associated waveforms and command tables.

As in the regular case, it's important to respect the order of upload of sequence, waveforms and command table. This can be done by doing that after the compilations futures are done

```python
# Generate a more complex example, where every sequence has associated waveforms and command table

from numpy.random import default_rng
rng = default_rng()

WFM_NUM = 24        #Number of waveforms
CT_NUM = 15000      #Number of calls to `executeTableEntry`

sequences = []
command_tables = []

for i in range(num_cores):
    #Generate a sequence of random `executeTableEntry`
    seq = Sequence()
    seq.code = dedent(f"""\
    // Core {i:d} sequence
    waitDigTrigger(1);  //Wait for a trigger to syncronize all the cores
    """)
    seq.code += "\n".join([f"executeTableEntry({rng.integers(WFM_NUM):d});" for _ in range(CT_NUM)])

    # Generate random waveform and associated command table to play them
    seq.waveforms = Waveforms()
    ct = CommandTable(ct_schema)
    ct.active_validation = False

    for j in range(WFM_NUM):
        # Random waveform parameters, gaussian
        wfm_len = rng.integers(2,100)*16
        x = np.linspace(-1, 1, wfm_len)
        sigma = rng.standard_normal()
        ampl = rng.random()

        seq.waveforms[j] = (ampl * np.exp( - x**2 / (2 * sigma**2) ))
        ct.table[j].waveform.index = j

    sequences.append(seq)
    command_tables.append(ct)
```

```python
with session.set_transaction(), ThreadPoolExecutor() as executor:
    #Compile and upload all the sequences
    # Get and store a future to verify the compilation once is done
    futures = {}
    for index, (awg_node, sequence) in enumerate(zip(awg_nodes, sequences)):
        future = executor.submit(awg_node.load_sequencer_program, sequence)
        futures[future] = index

    #Checks the errors
    # Iterate over all futures to verify the compilation
    # Then, upload waveforms and command table. This step is done here, to be sure
    # such upload is done only after the sequence. Since the futures are available as soon as
    # the compilation is done, their order is not predictable
    for future in as_completed(futures):
        index = futures[future]
        try:
            _ = future.result()
            awg_nodes[index].write_to_waveform_memory(sequences[index].waveforms)
            awg_nodes[index].commandtable.upload_to_device(command_tables[index])
        except CoreError as e:
            print("Compilation error on core", index, e)
```
