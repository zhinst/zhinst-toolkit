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
3.8 is not supported, we recommend to use Python 3.7. After installation, it is 
recommended to create a new environment. This can be done by opening the 
Anaconda Prompt from the start menu and by typing these lines in the prompt

.. code:: bash

    $ conda create -n NAME python=3.7
    $ conda activate NAME

where NAME should be the name of the envirronment that you want to create. The 
first line will create the environment, while the second activate it.


Installation
^^^^^^^^^^^^


Install the latest release
-----------------------------

Simply install the toolkit using `pip`

.. code:: bash

    $ pip install zhinst-toolkit

and verify the installation with e.g. iPython (if installed):

.. code:: bash

    $ ipython
    >>> import zhinst.toolkit as tk


Install from source
-------------------

Clone the :mod:`zhinst-toolkit` repository from the GitHub repository 
[here](https://github.com/zhinst/zhinst-toolkit) and install the package from 
source.

.. code:: bash

    $ git clone <TODO: add link to github repo>
    $ cd zhinst-toolkit
    $ pip install -r requirements.txt
    $ pip install .



Update
------

In case you have installed the :mod:`zhinst-toolkit` with `pip`, simply run

.. code:: bash

    $ pip install --upgrade zhinst-toolkit

If you have installed the toolkit from GitHub, pull the latest changes and rerun 

.. code:: bash

    $ pip install .


Start using the :mod:`zhinst-toolkit`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For an interactive use of the :mod:`zhinst-toolkit` we recommend 
`Jupyter Notebook`, `Jupyter Lab` or simply `iPython` for you console. 

.. code:: python

    >>> import zhinst.toolkit as tk
    >>> ...
    >>> hdawg = tk.HDAWG("hdawg1", "dev8006", interface="usb")
    >>> hdawg.setup()
    >>> hdawg.connect_device()
    >>> ...

Of course you are free to use it in the same way within a plain Python script.