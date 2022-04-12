Contributing to Zhinst Toolkit
=============================

Development environment setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Clone the `zhinst-toolkit` repository

    .. code-block:: sh

        $ git clone https://github.com/zhinst/zhinst-toolkit
        $ cd zhinst-toolkit

- Create virtual environment if you wish to run tests

- Install the dependencies

    .. code-block:: sh

        $ pip install -r requirements.txt

- Add zhinst-toolkit to `zhinst` package namespace by running the script
  to create a symbolic link between development files and zhinst-package.

    .. note:: 

        Windows: Requires administration privileges.

    .. code-block:: sh
    
        $ python .\scripts\zhinst_toolkit_symlink.py

Running the unit tests
~~~~~~~~~~~~~~~~~~~~~~

Running pytest

    .. code-block:: sh

        $ pytest

Running coverage
~~~~~~~~~~~~~~~~

    .. code-block:: sh

        $ pip install coverage
        $ coverage run -m pytest
        $ coverage html

The report can be seen in your browser by opening `htmlcov/index.html`.

Building the documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Zhinst-toolkit uses `Sphinx <https://pypi.org/project/Sphinx/>`_ to build the package documentation.

- Install the package in editable mode

    .. code-block:: sh

        $ pip install -e .

Change to docs directory

    .. code-block:: sh

        $ cd docs

- Install the dependencies

    .. code-block:: sh

        $ pip install -r requirements.txt

- Build the HTML documentation with Sphinx

    .. code-block:: sh

        $ make html

The generated documentation can be seen in your browser by opening `docs/html/index.html`.
