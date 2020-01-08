# ZI_driver_wrapper

This module contains instrument drivers for the HDAWG and UHFQA.

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

To set up and execute the ziPython `awgModule` the drivers provide a `hd.setup_awg(0)` method. 
