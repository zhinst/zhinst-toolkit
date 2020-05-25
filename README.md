![CI](https://github.com/zhinst/zhinst-toolkit/workflows/CI/badge.svg?branch=master)
[![Coverage](https://codecov.io/gh/zhinst/zhinst-toolkit/branch/master/graph/badge.svg?token=VUDDFQE20M)](https://codecov.io/gh/zhinst/zhinst-toolkit)
[![PyPI version](https://badge.fury.io/py/zhinst-toolkit.svg)](https://badge.fury.io/py/zhinst-toolkit)
[![DOI](https://zenodo.org/badge/245159715.svg)](https://zenodo.org/badge/latestdoi/245159715)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/fold_left.svg?style=social&label=Follow%20%40zhinst)](https://twitter.com/zhinst)


# Zurich Instruments Toolkit (zhinst-toolkit)
The Zurich Instruments Toolkit (zhinst-toolkit) is a collection of Python tools for high level device control. Based on the native interface to [Zurich Instruments LabOne](https://www.zhinst.com/labone), they offer an easy and user-friendly way to control Zurich Instruments devices. It's tailord for the control of multiple instruments together, especially for device management and multiple AWG distributed control. The Toolkit forms the basis for instrument drivers used in [QCoDeS](https://qcodes.github.io/Qcodes/) and [Labber](http://labber.org/online-doc/html/). It comes in the form of a package compatible with Python 3.6+.

For QCoDeS and Labber drivers for Zurich Instruments devices see [here](https://github.com/zhinst/zhinst-qcodes) and [here](https://github.com/zhinst/zhinst-labber).  

## Status
The zhinst-toolkit is well tested and considered stable enough for general usage. The interfaces may have some incompatible changes between releases. Please check the changelog if you are upgrading.

## Install

Install the package with pip:

```
pip install zhinst-toolkit
```

See [INSTALL](INSTALL.md) for more information.

## Documentation
For a full documentation see [here](https://docs.zhinst.com/zhinst-toolkit/en/latest).

## Contributing
We welcome contributions by the community, either as bug reports, fixes and new code. Please use the GitHub issue tracker to report bugs or submit patches. Before developing something new, please get in contact with us.

## License
This software is licensed under the terms of the MIT license. See [LICENSE](LICENSE) for more detail.