![CI](https://github.com/zhinst/zhinst-toolkit/workflows/CI/badge.svg?branch=main)
[![Coverage](https://codecov.io/gh/zhinst/zhinst-toolkit/branch/main/graph/badge.svg?token=VUDDFQE20M)](https://codecov.io/gh/zhinst/zhinst-toolkit)
[![PyPI version](https://badge.fury.io/py/zhinst-toolkit.svg)](https://badge.fury.io/py/zhinst-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/fold_left.svg?style=social&label=Follow%20%40zhinst)](https://twitter.com/zhinst)


# Zurich Instruments Toolkit (zhinst-toolkit)
The Zurich Instruments Toolkit (zhinst-toolkit) is a high level driver package
that allows communication with Zurich Instruments devices from the Python
programming language. It is based on top of the native
[Python API](https://pypi.org/project/zhinst-core/) (``zhinst.core``) of LabOne®,
the Zurich Instruments control software. It comes in the form of a package
compatible with Python 3.7+.

The central goal of zhinst-toolkit is to provide a pythonic approach to interact
with any Zurich Instruments device and is intended as a full replacement for the
low level ``zhinst.core`` package.

## Status
The zhinst-toolkit is well tested and considered stable enough for general usage.
The interfaces may have some incompatible changes between releases.
Please check the changelog if you are upgrading.
## LabOne software
As prerequisite, the LabOne software version 22.02 or later must be installed.
It can be downloaded for free at
[https://www.zhinst.com/labone](https://www.zhinst.com/labone). Follow the
installation instructions specific to your platform. Verify that you can
connect to your instrument(s) using the web interface of LabOne. If you are
upgrading from an older version, be sure to update the firmware of al your
devices using the web interface before continuing.

In principle LabOne can be installed in a remote machine, but we highly
recommend to install on the local machine where you intend to run the experiment.

## Install

Install the package with pip:

```
pip install zhinst-toolkit
```

## Documentation
For a full documentation see [here](https://docs.zhinst.com/zhinst-toolkit/en/latest).

## Contributing
We welcome contributions by the community, either as bug reports, fixes and new
code. Please use the GitHub issue tracker to report bugs or submit patches.
Before developing something new, please get in contact with us.

Please see [Contributing section](https://docs.zhinst.com/zhinst-toolkit/en/latest/contributing/)

## License
This software is licensed under the terms of the MIT license.
See [LICENSE](LICENSE) for more detail.
