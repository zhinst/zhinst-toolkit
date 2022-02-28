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

# Generate a Rabi Sequence


Requirements:

* LabOne >= 22.02
* Instruments:
    1 x SHFSG

```python
from zhinst.toolkit import Session

session = Session('localhost')
device = session.connect_device("DEVXXXX")
```

### Rabi Sequence parameter configuration

```python
CHANNEL = 0
# Center Frequency of the synthesizer
RF_FREQUENCY_HZ = 1e9
# Frequency of digital sine generator
OSC_FREQ_HZ = 100e6
OUTPUT_POWER_DBM = 0
```

### Configure center frequency and RF output

```python
device.sgchannels[0].configure_channel(
    enable=True,
    output_range=0,
    center_frequency=RF_FREQUENCY_HZ,
    rf_path=True
)
```

### Configure digital demodulation

```python
with device.set_transaction():
    # Set modulation frequency
    device.sgchannels[0].oscs[0].freq(OSC_FREQ_HZ)
    # Set sine generator
    device.sgchannels[0].sines[0].oscselect(0)
    # Set harmonic of sine generator
    device.sgchannels[0].sines[0].harmonic(1)
    # Set phase of sine generator
    device.sgchannels[0].sines[0].phaseshift(0)
    # Enable digital modulation
    device.sgchannels[0].awg.modulation.enable(1)
    # Set marker source
    device.sgchannels[0].marker.source(0)
```

### Load sequencer code

```python
SEQUENCER_CODE = """\
// Define constants in time domain
const t_wid = 50e-9;
const t_len = t_wid*8;
const amp = 1;
const n_amps = 101;
const n_aves = 1000;
const t_readout = 1e-6;

// Convert to samples
const s_rate = 2.0e9;
const s_wid = t_wid*s_rate;
const s_len= round(s_rate*t_len/16)*16; //Account for waveform granularity of 16 samples
const s_readout = round(s_rate*t_readout/16)*16;

// Define waveform and assign index
wave w = gauss(s_len, amp, s_len/2, s_wid);
assignWaveIndex(1,2,w,1,2,w,0);

// Reset oscillator phases and trigger scope
resetOscPhase();
setTrigger(1);
setTrigger(0);

//First Rabi amplitude and readout
executeTableEntry(0);
playZero(s_readout);

//Increment Rabi amplitude each loop iteration
repeat (n_amps-1) {
  resetOscPhase();
  setTrigger(1);
  setTrigger(0);

  executeTableEntry(1);
  //Readout window
  playZero(s_readout);
}
"""
device.sgchannels[0].awg.load_sequencer_program(SEQUENCER_CODE)
```

### Create and upload command table

```python
from zhinst.toolkit import CommandTable

ct_schema = device.sgchannels[0].awg.commandtable.load_validation_schema()
ct = CommandTable(ct_schema)

ct.table[0].waveform.index = 0
ct.table[0].amplitude00.value = 0.0
ct.table[0].amplitude00.increment = False
ct.table[0].amplitude01.value = -0.0
ct.table[0].amplitude01.increment = False
ct.table[0].amplitude10.value = 0.0
ct.table[0].amplitude10.increment = False
ct.table[0].amplitude11.value = 0.0
ct.table[0].amplitude11.increment = False

ct.table[1].waveform.index = 0
ct.table[1].amplitude00.value = 0.007
ct.table[1].amplitude00.increment = True
ct.table[1].amplitude01.value = -0.007
ct.table[1].amplitude01.increment = True
ct.table[1].amplitude10.value = 0.007
ct.table[1].amplitude10.increment = True
ct.table[1].amplitude11.value = 0.007
ct.table[1].amplitude11.increment = True

device.sgchannels[0].awg.commandtable.upload_to_device(ct)
```

### Run the sequencer

```python
device.sgchannels[0].awg.enable_sequencer(single=True)
```
