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

# Save and load device settings

Demonstrate how to save and load the settings of a device. The LabOne device
settings module is used for this purpose and makes this process reproducible
and platform independent, e.g. the result can be used in the LabOne UI and vice versa.

Requirements:

* LabOne Version >= 22.08
* Instruments:
    1 x Any Zurich Instrument device

```python
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
# For HF2 devices
# session = Session('localhost', hf2=True)
# device = session.connect_device("DEVXXXX", HF2=True)
```

### Simple save and load

The device settings module is a LabOne native module and work accross all APIs, including the UI.
Its main purpose is to store the current state of a device to a file or reapply them at any time.

> **Warning:**
>
> Although it is possible to used the device settings module to load all settings
> from the device, it is not recommended and we will see much more efficient ways
> during this example.

The device settings module in zhinst-toolkit has two helper functions `save_to_file` and `load_from_file` defined 
for easy and safe usage. These functions use a temporary LabOne module to avoid unwanted side effects. 

```python
from pathlib import Path
session.modules.device_settings.save_to_file(Path("test.xml"), device)
```

```python
session.modules.device_settings.load_from_file(Path("test.xml"), device)
```

The resulting xml file contains all information necessary to recreate the device state
and can for example be reapplied in the LabOne UI.

These two function work synchronously which is in general the desired behaviour.
The next section will cover the the asynchronous operations for more experienced users.

### Asynchronous save and load

The helper function are a synchronously operation and sometimes (e.g. when loading 
or storing settings from  more than one device) it is usefull and faster to 
do the operations asynchronously. This requires to set up the device settings 
module manually. The configuration is done through nodes like with any other settings
inside LabOne.

```python
from pathlib import Path
device_settings = session.modules.device_settings
filename = Path("test.xml")

device_settings.device(device)
device_settings.filename(filename.stem)
device_settings.path(filename.parent)
device_settings.command("save")
```

After the configuration of the module is finished the process can be started.

```python
device_settings.execute()
```

Once we want to ensure that the save process is finished we wait_for the `finished`
node to become true.

```python
device_settings.finished.wait_for_state_change(1)
```

Applying settings from an existing settings file is done in the same way. The only
difference is the `command` node needs to be set to "load". 

> **Warning:**
>
> Although loading settings can also be done asynchronously, e.g. loading settings
> for multiple devices simultaneously. Using the device or changing settings will 
> result in undefined behaviour.

### Getting the current settings from the device

Although the device settings module is able to read the settings from a device 
(without going through a file) zhinst-toolkit offers easier and more efficient
ways for that. Simply by using the nodetree, that supports calling non lead nodes.

Calling the root of a nodetree returns all node values.

```python
len(device())
```

Calling a non leaf node returns all child lead nodes.

```python
device.features()
```

> **Note:**
> 
> Only setting nodes are returned by calling non leaf nodes. Streaming nodes will not be included.
