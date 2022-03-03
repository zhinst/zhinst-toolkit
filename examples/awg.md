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
and are available behind the ``/awg`` node.

Connect devices and access the ``/awg`` node.

```python
from zhinst.toolkit import Session

session = Session('localhost')
device = session.connect_device("DEV8541")
awg_node = device.awgs[0]
```

## Compile and Upload Sequencer Program

The Sequencer program can be uploaded as string.

```python
SEQUENCER_CODE = """\
// Define waveforms
wave w0_1 = placeholder(1008, true);
wave w0_2 = placeholder(1008, true);
wave w1_1 = placeholder(1008);
wave w1_2 = placeholder(1008);
// Assign waveforms to an index in the waveform memory
assignWaveIndex(1,2,w0_1,1,2,w0_2,0);
assignWaveIndex(1,2,w1_1,1,2,w1_2,2);
// Play wave 1
playWave(1,w0_1,2,w0_2);
waitWave();
// Play wave 2
playWave(1,w1_1,2,w1_2);
waitWave();
"""

awg_node.load_sequencer_program(SEQUENCER_CODE)
```

```python
session.daq_server.listNodes("/DEV8541/AWGS/0/WAVEFORM")
```

```python
awg_node.enable_sequencer(single=True)
awg_node.wait_done()
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

The ``Waveform`` class is a mutuable mapping, meaning it behaves similiar to a
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

wave1 = np

waveforms = Waveforms()
# Waveform at index 0 with markers
waveforms[0] = (0.5*np.ones(1008), -0.2*np.ones(1008), np.ones(1008))
# Waveform at index 2 without markers
waveforms[2] = (np.random.rand(1008)), np.random.rand(1008)

awg_node.write_to_waveform_memory(waveforms)
```

> Note:
>
> The waveform data can also be assigned via the helper function
> ``assign_waveform`` which converts the data into the same tuple
> as used above. Similiar ``assign_native_awg_waveform`` can be used to
> assign already to a single native AWG format array converted waveform data to
> an index.


The same way one can upload the waveforms through a simple function one can also
download the waveforms from the device

```python
waveforms_device = awg_node.read_from_waveform_memory()
waveforms_device[0]
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

The command tables is specified in the JSON format and need to comform to a device
specific schema. The user manuals explain in detail how the command table is
structured and used. Similar to the Waveforms zhinst-toolkit offers a helper class
for the comman table usage called ``CommandTable``.

> Note:
>
> Since the command table structure is defined in a JSON schema the ``CommandTable``
> class requires this json schema as well. Either one stores a copy of it locally or
> it can be accessed in zhinst-toolkit through the function ``load_validation_schema``

```python
# Load the existing command table from the device
ct = awg_node.commandtable.load_from_device()

# Another way to create a CommandTable instance is by using the schema
from zhinst.toolkit import CommandTable
ct_schema = awg_node.commandtable.load_validation_schema()
ct = CommandTable(ct_schema)

ct.as_dict()
```

The ``CommandTable`` class creates a pythonic approach of creating a command table
that is similar to the node tree usage in zhinst-toolkit. Elements can be accessed
either by value or by attribute.

Autocompletion is also available as well as on the fly validation.

```python
dir(ct.table[0])
```

```python
ct.table[0].amplitude0.info()
```

```python
ct.table[0].amplitude0.info("value")
```

```python
ct.table[0].amplitude0.value = 0.5
ct.table[0].amplitude0.value
```

```python
ct.table[0].amplitude0.value = 2
```

Each change to the command table will be validated on the fly. In addition
the moment it gets converted the complete structure is validated.

```python
ct.clear()
ct.table[0].amplitude0.increment = True
ct.as_dict()
```

Once the command table is finished the upload to the device is taken care of
by zhinst-toolkit

```python
ct.clear()
ct.table[0].waveform.index = 0
ct.table[0].amplitude0.value = 0.0
ct.table[0].amplitude0.increment = False
ct.table[0].amplitude1.value = -0.0
ct.table[0].amplitude1.increment = False

ct.table[1].waveform.index = 0
ct.table[1].amplitude0.value = 0.007
ct.table[1].amplitude0.increment = True
ct.table[1].amplitude1.value = -0.007
ct.table[1].amplitude1.increment = True

awg_node.commandtable.upload_to_device(ct)
```
