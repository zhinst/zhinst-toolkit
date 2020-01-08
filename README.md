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
qa.set("qas/0/integration/weights/0/real")  # > {'qas/0/integration/weights/0/real': array([0.25, 0.25, 0.25, ..., 0.  , 0.  , 0.  ], dtype=float32)}
```

