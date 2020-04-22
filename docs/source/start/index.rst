Getting Started
===============



Requirements
^^^^^^^^^^^^

LabOne
------

As prerequisite, the `LabOne` software version 20.01 or later must be installed.
It can be downloaded for free at https://www.zhinst.com/labone. Follow the 
installation instructions specific to your platform. Verify that you can connect 
to your instrument(s) using the web interface of `LabOne`. If you are upgrading 
from an older version, be sure to update the firmware of all your devices using 
the web interface before continuing.

Anaconda
--------

A working installation of Python 3.6+ is required to use :mod:`zhinst-toolkit`. 
On Windows and MacOS X, Anaconda is highly recommended. At the moment Python 
3.8 is not supported, we recommend to use Python 3.7. After installation, is 
recommended to create a new envirornment. This can be done by opening the 
Anaconda Prompt from the start menu and by typing these lines in the prompt

.. code:: bash

    $ conda create -n NAME python=3.7
    $ conda activate NAME

where NAME should be the name of the envirornment that you ant to create. The 
first line will create the envirornment, while the second activate it.


Installation
^^^^^^^^^^^^


Install the Latest Release
-----------------------------

Simply install the toolkit using `pip`

.. code:: bash

    $ pip install zhinst-toolkit

and verify the installation with

.. code:: bash

    $ ipython
    >>> import zhinst.toolkit as tk


Install from Source
-------------------

Clone the :mod:`zhinst-toolkit` repository from github HERE (TODO: add link!) 
and install the package from source.

.. code:: bash

    $ git clone <TODO: add link to github repo>
    $ cd zhinst-toolkit
    $ pip install -r requirements.txt
    $ pip install -e .

The `-e` option installs the package in `editable` mode. That means you can make 
local changes to it without having to reinstall it.


Update
------

In case you have installed the :mod:`zhinst-toolkit` with `pip`, simply run

.. code:: bash

    $ pip install --upgrade zhinst-toolkit

If you have installed the toolkit from GitHub, pull the latest changes and rerun 

.. code:: bash

    $ pip install .


Using the :mod:`zhinst-toolkit`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For an interactive use of the :mod:`zhinst-toolkit` we recommend 
`Jupyter Notebooks`, `Jupyter lab` or simply `ipython` for you console. 

.. code::

    >>> import zhinst.toolkit as tk
    >>> ...
    >>> hdawg = tk.HDAWG("hdawg1", "dev8006", interface="usb")
    >>> hdawg.setup()
    >>> hdawg.connect_device()
    >>> ...

Of course you are free to use it in the same way within a plain Python script.