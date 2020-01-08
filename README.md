# ZI_driver_wrapper

This module contains instrument drivers for the HDAWG and UHFQA. Drivers for QCoDeS, Labber and QCCS can make use of this wrapper as a common basis. Its functionality facilitates the device interface and usability. The `drivers` module can also be tested independently of the QCoDeS or Labber implementations, currently the code coverage of unit and integration tests is at roughly 90%.  

# Usage

See also `example.py`.

```python
from drivers import HDAWG, UHFQA
```

Both drivers inherit from a general `Device` class that establishes a device connection and implements `set()` and `get()` methods.

```python
qa = UHFQA()
qa.connect("dev2266")

# set nodes
qa.set("sigouts/*/on", 1)
qa.set("qas/0/integration/weights/0/real", np.ones(4096))
qa.set([
    ("qas/0/result/length", 1000),
    ("qas/0/result/averages", 64),
    ("qas/0/result/source", 7)
])

# get nodes
qa.get("sigouts/*/on")                      # > {'sigouts/0/on': 1, 'sigouts/1/on': 0}
qa.get("sigouts/*/on", valueonly=True)      # > [1, 0]
qa.get("qas/0/integration/weights/0/real")  # > {'qas/0/integration/weights/0/real': array([0.25, 0.25, 0.25, ..., 0.  , 0.  , 0.  ], dtype=float32)}
```

## AWG

The `AWG` class controls the AWG sequencers of each device. `HDAWG` and `UHFQA` each hold four or respectively one `AWG` object. They can be addressed as a property through `hd.awgs[0]` or `qa.awg`.

AWG sequences are programmed using the `awg.set(**kwargs)` command with arguments that correspond to seuqence parameters. Most importantly, `sequence_type` sets the type of the sequence:
* `"Simple"` allows upload of waveforms
* `"Rabi"` implements a Rabi sequence with DRAG pulses on the two quadratures
* `"T1"` and `"T2*"` implement T1 or T2 Ramsey sequences  

Other sequence parameters include `trigger_mode`, `repetitions`, `period`, ... A dictionary with the current sequence parameters is returned by `awg.sequence_params`, e.g.

```python
hd.awgs[0].sequence_params
# {'sequence_type': None,
#  'sequence_parameters': {'target': 'HDAWG',
#   'clock_rate': 2400000000.0,
#   'period': 0.0001,
#   'trigger_mode': 'None',
#   'repetitions': 1,
#   'n_HW_loop': 1,
#   'dead_time': 5e-06,
#   'trigger_delay': 0,
#   'latency': 1.6e-07,
#   'trigger_cmd_1': '//',
#   'trigger_cmd_2': '//',
#   'wait_cycles': 0,
#   'dead_cycles': 0}}
```

To set up and execute the ziPython `awgModule` the drivers provide a `hd.setup_awg(0)` method. Afterwards, the the AWG can be updated which sends the current sequnece program to the device and compiles it. In `"Simple"` mode waveforms can be added and the uploaded to the device.

```python
hd.awgs[0].set(
    sequence_type="Rabi",
    period=period,
    trigger_mode="Send Trigger",
    clock_rate=hd.get("system/clocks/sampleclock/freq", valueonly=True),
    pulse_amplitudes=np.linspace(0, 1.0, 100),
    pulse_width=20e-9,
    pulse_truncation=4,
    repetitions=repetitions
)
hd.awgs[0].update()

qa.awg.set(
    sequence_type="Simple",
    period=period,
    trigger_mode="External Trigger",
    clock_rate=1.8e9,
    repetitions=repetitions_RO
)
x = np.linspace(0, 180, 3200)
qa.awg.add_waveform(np.sin(x), np.cos(x))
qa.awg.upload_waveforms()

hd.awgs[0].run()
time.sleep(0.1)
qa.awg.run()
```

See `example.py` for more.
