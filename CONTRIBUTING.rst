Ways to contribute
==================

* Opening a new ticket to `Issues`_ or by commenting on existing one with new solutions or suggestions
* By improving the project `documentation`_.
* By improving and adding new project `examples`_.
* By contributing code; bug fixes, new features and so on.

.. _Issues: https://github.com/zhinst/zhinst-toolkit/issues
.. _documentation: https://docs.zhinst.com/zhinst-toolkit/en/latest/
.. _examples: https://docs.zhinst.com/zhinst-toolkit/en/latest/examples/index.html

Code contributions
==================

* Follow `PEP8 <https://peps.python.org/pep-0008/>`_ and you should be fine.

* The project uses `Google Style Python docstrings <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_

* The project uses `black`, `flake8` and `mypy` to check for code style.

Development environment setup
-----------------------------

- Clone the `zhinst-toolkit` repository

    .. code-block:: sh

        $ git clone https://github.com/zhinst/zhinst-toolkit
        $ cd zhinst-toolkit

- Create a Python virtual environment

- Install the dependencies

    .. code-block:: sh

        $ pip install -r requirements.txt

- Add zhinst-toolkit to `zhinst` package namespace by running the script
  to create a symbolic link between development files and zhinst-package.

    .. note:: 

        Windows: Requires administration privileges.

    .. code-block:: sh
    
        $ python .\scripts\zhinst_toolkit_symlink.py

Running the tests
-----------------

Running all tests
~~~~~~~~~~~~~~~~~

    .. code-block:: sh

        $ pytest

Running lint test
~~~~~~~~~~~~~~~~~

    .. code-block:: sh

        $ tox -e lint

Running typing tests
~~~~~~~~~~~~~~~~~~~~

    .. code-block:: sh

        $ tox -e typing

Running code format check
~~~~~~~~~~~~~~~~~~~~~~~~~

    .. code-block:: sh

        $ tox -e black

Running coverage
~~~~~~~~~~~~~~~~

    .. code-block:: sh

        $ pip install coverage
        $ coverage run -m pytest
        $ coverage html

The report can be seen in your browser by opening `htmlcov/index.html`.

Building the examples
---------------------

The examples are stored as Markdown files. If you wish to turn the local 
`examples/*.md` files into Jupyter Notebooks by using the following script:

    .. code-block:: sh

        $ python scripts/generate_notebooks.py local

Building the documentation
--------------------------

Zhinst-toolkit uses `Sphinx <https://pypi.org/project/Sphinx/>`_ to build the package documentation.

- Install the package in editable mode

    .. code-block:: sh

        $ pip install -e .

Change to docs directory

    .. code-block:: sh

        $ cd docs

- Install the docs dependencies

    .. code-block:: sh

        $ pip install -r docs/requirements.txt

- Build the HTML documentation along with examples with Sphinx

    .. code-block:: sh

        $ make html [local | remote]

The generated documentation can be seen in your browser by opening `docs/html/index.html`.

Pull requests
--------------

Use `Github pull requests <https://github.com/zhinst/zhinst-toolkit/pulls>`_ to contribute your code.

Use an existing Pull request template and follow it.


Writing examples
================

Examples are a good way to demonstrate on how the library is used to execute various 
experiments and measurements. Examples using `zhinst Toolkit` are welcome.

File format
-----------

The examples are written by using Jupyter Notebooks, but version controlled as Markdown files.

The ready made example Notebooks can be translated to a Markdown file by using `Jupytext <https://jupytext.readthedocs.io/en/latest/>`_.

Structure
---------

Please see the existing examples in /examples and try to keep the same structure.
Including the output of Notebook cells is highly encouraged.

Adding to documentation
-----------------------

Version controlled Markdown files are translated to Notebooks in CI and
then to HTML for display.

To include the example in HTML documentation, create an NB link in `docs <https://github.com/zhinst/zhinst-toolkit/tree/main/docs/source/examples>`_.
