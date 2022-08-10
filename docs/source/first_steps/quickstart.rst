Quickstart
==========

Eager to get started? This page gives a good introduction to zhinst-toolkit.
Follow :doc:`installation` to install zhinst-toolkit first.

Preparation
-----------

LabOne® needs to installed and running before using zhinst-toolkit.
For a complete reference see the dedicated `user manual <http://docs.zhinst.com/>`_
page for your instrument(s).

Before continuing, make sure a LabOne® data server is running in your network and
all of your devices are visible.

Session To The Data Server
---------------------------

Zurich Instruments devices use a server-based connectivity methodology. Server-based
means that all communication between the user and the instrument takes place via a
computer program called a server, the Data Server. The Data Server recognizes available
instruments and manages all communication between the instrument and the host computer
on one side, and communication to all the connected clients on the other side.
(see `Architecture <https://docs.zhinst.com/labone_programming_manual/introduction.html#pm.intro.architecture>`_
in the LabOne Programming Manual)

The entry point into toolkit is therefore a API client session to a data server:

.. code-block:: python

    >>> from zhinst.toolkit import Session
    >>> session = Session("localhost")

(if your data server runs on a remote computer (e.g. an MFLI directly) replace
``localhost`` with the correct address.)

Node Tree
---------

All settings and data in LabOne® are organized by the Data Server in a file-system-like
hierarchical structure called the node tree. zhinst-toolkit implements the node tree in
a nested dictionary like structure. The interface of that dictionary also supports
accessing the nodes by attribute, making it more readable and simpler to write.
(For an in-depth introduction into the node tree structure in zhinst-toolkit take a look
at :doc:`Node Tree <nodetree>`)

.. code-block:: python

    >>> session.debug.level()
    'status'

So what did that code do?

1. The ``session`` represents the session to the data server and gives access to its nodes (``/zi/*`` in the core API).
2. One of these nodes is ``zi/debug/level``. The :doc:`Node Tree <nodetree>` allows it to access that node by attributes.
3. To get the current value of the node simply make a call operation.

Changing the value of a node can be done in a similar way. Simply add the value
to the call operation.

.. code-block:: python

    >>> session.debug.level('warning')
    >>> session.debug.level()
    'warning'

Device communication
--------------------

The data server can be connected to one or multiple devices. By connecting or accessing
an already connected device a new device object for that device is created by
zhinst-toolkit.

.. code-block:: python

    >>> session.devices.visible()
    ['dev1234', 'dev5678']
    >>> session.devices.connected()
    ['dev1234']
    >>> session.devices['dev1234']
    BaseInstrument(DEMO,dev1234)
    >>> session.connect_device('dev5678')
    BaseInstrument(DEMO,dev5678)

The created device object holds all device specific nodes and depending on the device
type also implements additional functionalities (e.g. exposes the
``zhinst.utils`` functions).

.. code-block:: python

    >>> device = session.devices['dev1234']
    >>> device.demods[0].freq()
    10e6
    >>> dir(device.demods[0])
    ['adcselect',
    'bypass',
    'enable',
    'freq',
    'sample',
    'trigger']

To see an overview of the device specific functionalities take a look at the dedicated
examples.


LabOne® modules
---------------

In addition to the usual API commands available for instrument configuration and data
retrieval the LabOne® API also provides a number of so-called *modules*: high-level
interfaces that perform common tasks such as sweeping data or performing FFTs.
(See the
`LabOne Programming Manual <https://docs.zhinst.com/labone_programming_manual/introduction_labone_modules.html>`_
For a complete documentation of all modules available)

In zhinst-toolkit these modules can be accessed through the ``session``. Similar to the
devices, each module can be controlled through a node tree. Some of the modules have
toolkit specific functionalities (e.g. reading the acquired data automatically).
To see an overview of the module specific functionalities, take a look at the dedicated
examples.

.. note::

    The underlying LabOne® module (zhinst.core object) can be accessed with the
    ``raw_module`` property

.. code-block:: python

    >>> daq_module = session.modules.daq
    >>> daq_module.grid.mode()
    4
    >>> daq_module.raw_module
    <zhinst.core.DataAcquisitionModule at 0x10edc5630>
