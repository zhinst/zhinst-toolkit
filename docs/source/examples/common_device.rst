Common
======

The following section gives an overview of the functionalities that
all devices have in common. Although special functions may be available for individual
devices, all devices supported by LabOne® can also be connected and used through
toolkit.

.. code-block:: python

    from zhinst.toolkit import Session

    >>> session = Session('localhost')
    >>> device = session.connect_device("DEVXXXX")
    >>> device.serial
    "DEVXXXX"
    >>> device.device_type
    "MFLI"

The first similarity is the :doc:`node tree <../first_steps/nodetree>`. It
allows not only the manipulation of all device specific settings, but also adds
functionality like subscribe/poll and filtering. A list of all device specific
nodes can be looked up in the respective `user manual <http://docs.zhinst.com/>`_.
One can also use the node tree to see available (child) nodes or to
access the node specific information.

.. code-block:: python

    >>> list(device.child_nodes())
    [/dev1234/oscs,
     /dev1234/demods,
     /dev1234/extrefs,
     /dev1234/triggers,
     /dev1234/status,
     ...]
    >>> list(device.demods[0].child_nodes(recursive=True))
    [/dev1234/demods/0/adcselect,
     /dev1234/demods/0/order,
     /dev1234/demods/0/rate,
     /dev1234/demods/0/oscselect,
     ...]

The node tree is automatically generated during the initialization of the device
in toolkit. It is based on the information provided by the device and therefore
adapts automatically to a new firmware.

Check Compatibility
-------------------

In general, Zurich Instruments only supports the latest versions of each software
component. Although in many cases it will have no influence on a measurement
if not all versions are up to date important feature or fixes by be missing.
To ensure that all versions match each device exposes a function called
``check_compatibility`` which only passes if all versions match.

The following criteria are checked:

* minimum required zhinst-utils package is installed
* minimum required zhinst-core package is installed
* zhinst package matches the LabOne Data Server version
* firmware revision matches the LabOne Data Server version¨

If any of the above criterion is not fulfilled ``check_compatibility`` will
raise RuntimeError.

Transactional Set
-----------------

The node tree has a context manager called ``set_transaction``. As described
in the :doc:`node tree <../first_steps/nodetree>` section, it is used to bundle
multiple set commands to different nodes into a single message to the data
server.

Each device in toolkit makes this function easily accessible through a property.

.. code-block:: python

    >>> with device.set_transaction():
            device.demods["*"].enable(1)
            device.demods[1].harmonic(3)
            device.demods[0].harmonic(2)
            device.demods[0].rate(2000)


.. warning::

    Since the transactions are performed on the device directly it is not
    possible to have a single transaction for multiple devices in toolkit.

.. note::

    A transaction only affects the operations settings nodes. Everything else
    will not be affected by the transaction. Functions to external packages like
    the device-utils are not affected by the transaction.

Factory reset
-------------

To reset a device to the factory settings LabOne has a default preset. All
toolkit device classes therefor expose a function called ``factory_reset`` which
loads the default preset.

.. code-block:: python

    >>> device.factory_reset()
    "Factory preset is loaded to device DEV1234."

.. note::

    Not all devices support the factory devices yet. If a device does not support
    the factory reset it will issue a warning when trying to call it. In that
    case a power cycle has the same effect.

