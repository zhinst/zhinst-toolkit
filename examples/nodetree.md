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

# Zurich Instruments Toolkit Node Tree

The core of toolkit is the node tree. It is also the main difference compared to the
lower level ``zhinst.core`` API.

## Background

All settings and data in LabOne® are organized by the data server in a file-system-like
hierarchical structure called the node tree. To manipulate or extracting the value of a
node one can issue a corresponding request to the data server. A basic request consists
of a absolute and unique path representing the node and in case of a set command the
desired value.

For example the node ``/DEV1234/DEMODS/0/FREQ`` indicates the frequency used inside
the demodulator 0, of the device with the id dev1234, for demodulation and output
generation. Issuing a simple get request to the data server would return the current
frequency in Hz.

Of course the LabOne® node tree offers much more functionality than getting or setting
nodes (e.g. subscription and asynchronous polling). zhinst.toolkit tries to map all of
these functionalities into a nested dictionary like structure. The interface of that
dictionary also supports accessing the nodes by attribute, making it more readable and
simpler to write.

> Note:
>
> although the zhinst.toolkit.nodetree can be used without a toolkit session, the
> following examples are based on a toolkit session for demonstration purpose. But all
> shown functionalities can be used without a toolkit session). In that case a instance
> of the NodeTree class can be created with a zhinst.core.ziDAQServer instance.

```python
from zhinst.toolkit import Session

session = Session("localhost")
device = session.connect_device("DEVXXXX")
device.root
```

## Accessing nodes

The nested dictionary is a lazy structure that offers a efficient and user-friendly
approach to the LabOne® node tree. It offers full support for Unix wildcards and nodes
can either be specified by attribute or by item.

Since the structure is lazy, meaning node objects are created on the fly and are
stateless, the user does not need to worry about long setup times or slow response
times.

```python
device.demods[0].freq
device["/demods/0/freq"]
device.demods["*"].freq
```

## Getting and Setting node values

The core functionality of each node is the overloaded call operator.
Making a call gets the value(s) for that node. Passing a value to the call
operator will set that value to the node on the device.

Calling a node that is not a leaf (wildcard or partial node) will return/set the
value on every node that matches it (the return type will be a dictionary or a mapping).

> Warning:
>
> Setting a value to a non leaf node will set the value of all child lead nodes.
> It should therefor be used with great care to avoid unintentional changes.

```python
device.demods[0].order()
```

```python
device.demods[0].order(2)
device.demods["*"].order()
```

```python
device.demods["*"].order(3)
device.demods["*"].order()
```

```python
device.auxins[0]()
```

The call operator support the following Flags:
* deep (default = False)
* enum (default = True)
* parse (default = True)

### deep

Flag if the set operation should be blocking until the data has been processed by the
device, respectively if the get operation should return the value from the device or
the cached value on the data server (if there is any). This flag is reset by
default because the operation can take significantly longer.

In addition to the value, a deep get operation will return the timestamp from the device
(The timestamp can be None, e.g. deep gets on LabOne modules).

```python
device.demods[0].freq(deep=True)
```

For a deep set the call operator will return the value acknowledged
by the device. e.g. important for floating point values with a
limited resolution.

> Warning:
>
> Does not work for wildcard nodes or non leaf nodes since they represent multiple
> nodes that are set in a transactional set which does not report the acknowledged
> values.

```python
device.demods[0].rate(1000, deep=True)
```

### enum

A lot of nodes in the nodetree are enumerated. Often the enumerated values have a
string representation. The Flag ``enum``, enabled by default, returns the string
representation of the value instead of the integer representation (where applicable).

```python
device.demods[0].enable()
```

```python
device.demods[0].enable(enum=False)
```

### parse

For some nodes toolkit implements special parsers that are called before setting or
getting a value. The flag ``parse``, that is enabled by default, controls whether
these functions should be applied or not.

One can also add own Parser functions to the nodetree on the fly. Both get and
set parser take a value and must return a value.

```python
def get_print(value):
    print(f"Received <{value}> from LabOne")
    return value

def set_print(value):
    print(f"Will send <{value}> to LabOne")
    return value

device.root.update_node(
    device.demods[0].enable,
    {
        "GetParser": get_print,
        "SetParser": set_print,
    }
)

device.demods[0].enable("on")
device.demods[0].enable(parse= False)
```

## Transactions

Setting up an experiment normal requires setting a couple of nodes to the correct
value. Since every call operation triggers an individual message to the data
server, this can take a noticeable amount of time. To avoid this LabOne® offers
an API functionality called transactional set. This functionality enables the user
to bundle multiple set commands into a single command/message. In zhinst.toolkit
the functionality of a transactional set is wrapped in a context manager
(``with`` statement). Every set operation within this context will be buffered
and send to the data server in a single transaction at the end of the scope.

```python
with device.set_transaction():
    device.demods["*"].enable(1)
    device.demods[1].harmonic(3)
    device.demods[0].harmonic(2)
    device.demods[0].rate(2000)
```

The transaction only effects the set operations, all other functionality of
the nodetree is not affected by it.

Apart form the above shown device level transaction toolkit also implements a 
session wide transaction. This type of transaction bundles every set command 
for all devices connected to this session. 

> Note:
>
> The order of the set commands is maintained.

```python
with session.set_transaction():
    device.demods["*"].enable(1)
    device.demods[1].harmonic(3)
    device.demods[0].harmonic(2)
    device.demods[0].rate(2000)
```

## Node Information

Besides the call operator, the nodetree structure in toolkit offers much more
functionality. One of them is the additional information that LabOne provides
for each node. They can be accessed on each leaf node through the ``node_info``
property.

```python
device.demods[0].enable.node_info
```

```python
print(device.demods[0].enable.node_info)
```

```python
dir(device.demods[0].enable.node_info)
```

```python
print(device.demods[0].enable.node_info.path)
print(device.demods[0].enable.node_info.writable)
print(device.demods[0].enable.node_info.options)
```

## Node Functions

As mentioned above the node tree exposes all functionalities from LabOne® for
manipulating nodes. The following section gives a brief overview of how these
functionalities are exposed in toolkit.

### Subscribe / Unsubscribe

Each node has a method called ``subscribe`` and the counter part ``unsubscribe``.
(subscribing to wildcard nodes or partial nodes is also supported).

After a node has been subscribed value changes will be buffered within the data
server and can be polled from the session. The poll command on the session
returns a dictionary of nodes and their corresponding data.

> Note:
>
> The data server buffers the subscribed data for each session independently.
> Subscribing or unsubscribing does therefor only affect the current session

> Note:
>
> It is not possible to poll the data for a single node. One can only poll the
> data on the session and the result will contain the data for all subscribed
> data within a session.

```python
import time
device.demods[0].sample.subscribe()
data = session.poll()
device.demods[0].sample.unsubscribe()
data[device.demods[0].sample]
```

### Get as event (asynchronous get)

The above described call operator is a synchronous get request. Meaning it will
block until it receives the data from the data server or the device (in case of
a deep get). LabOne® also provides the interface for a asynchronous get. In
toolkit each node has a function called ``get_as_event``. It will add the current
value of that node into the buffer of the Data Server. The next poll command will
return that value.

```python
device.demods[0].freq.get_as_event()
session.poll()
```

### Wait for state change

Sometimes it is necessary to hold the  until a node has a specific value.
One common example is that for some operations the device resets a node value
to signal that a measurement is complete.

The function ``wait_for_state_change`` blocks until the node has the specified
value (or the timeout has exceeded).

```python
device.extrefs[0].enable(0, deep=True)
device.extrefs[0].enable(1)
try:
    device.extrefs[0].locked.wait_for_state_change(1, timeout=0.1)
except TimeoutError:
    print("Could not lock to the external reference. Please make sure an external reference is supplied.")
```

It is also possible to wait until the node has any value except the one specified.

```python
device.extrefs[0].enable(0, deep=True)
device.extrefs[0].enable(1)
try:
    device.extrefs[0].locked.wait_for_state_change(0, invert=True)
except TimeoutError:
    print("Could not lock to the external reference. Please make sure an external reference is supplied.")
```

### Filter nodes

LabOne® offers a node filter mechanism. In toolkit this filtering is implemented
in the ``child_nodes`` function.

Without any additional flags it returns all the leaf nodes that belong to that node.
(Leaf nodes will return themselves, wildcard and partial nodes will return their
child nodes).

Since the list of nodes that will be returned is potentially very large, the
``child_nodes`` function returns a generator.

```python
device.demods[0].child_nodes()
```

```python
list(device.pids[0].child_nodes())
```

``child_nodes`` accepts the following list of flags to filter the return value:

* recursive: Returns the nodes recursively
* leavesonly: Returns only nodes that are leaves, which means they are at the
  outermost level of the tree.
* settingsonly: Returns only nodes which are marked as setting.
* streamingonly: Returns only streaming nodes.
* subscribedonly: Returns only subscribed nodes.
* basechannelonly: Return only one instance of a node in case of multiple
  channels.
* excludestreaming: Exclude streaming nodes.
* excludevectors: Exclude vector nodes.

The following command returns for instance all streaming nodes of the device,
but only includes the base channel.

```python
list(device.child_nodes(recursive=True, streamingonly=True, basechannelonly=True))
```
