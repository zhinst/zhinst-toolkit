# Installation

## LabOne software
As prerequisite, the LabOne software version 20.01 or later must be installed. 
It can be downloaded for free at [https://www.zhinst.com/labone](https://www.zhinst.com/labone). Follow the installation instructions specific to your platform. Verify that you can connect to your instrument(s) using the web interface of LabOne. If you are upgrading from an older version, be sure to update the firmware of al your devices using the web interface before continuing.

In principle LabOne can be installed in a remote machine, but we highly recommend to install on the local machine where you intend to run the experiment.

## Anaconda
A working installation of Python 3.6+ is required to use zhinst-toolkit. On Windows and MacOS X, [Anaconda](https://www.anaconda.com/download) is highly recommended. At the moment Python 3.8 is not supported, we recommend to use Python 3.7.

After installation, is recommended to create a new envirornment. This can be done by opening the *Anaconda Prompt* from the start menu and by typing these lines in the prompt
```shell script
conda create -n NAME python=3.7
conda activate NAME
```
where *NAME* should be the name of the envirornment that you ant to create. The first line will create the envirornment, while the second activate it.

Linux users may use Anacoda or the system Python installation. In this case, virtualenv or venv are recommended.

## Installing the latest release
This installation methos is recommended for the majority of the users that don;t need to modify the zhinst-toolkit package.
zhinst-toolkit is packaged on PyPI, so it's enough to write in the prompt
```shell script
pip install zhinst-toolkit
```

## Upgrading to a new release
The upgrade is very similar to the installation; from the prompt type
```shell script
pip install --upgrade zhinst-toolkit
```
The upgrade is highly recommended if you are upgrading LabOne as well.

## Installing the development version
If you need to modify the zhinst-toolkit package or you need a fature that it's not in the release yet, you may install the development version. This is recommended only to advanced users with advanced knowledge of Python and Git.
Clone the zhinst-toolkit repository from GitHub from [https://github.com/zhinst/zhinst-toolkit](https://github.com/zhinst/zhinst-toolkit).
Then move to the root of repository and install it with
```shell script
python setup.py install
```
Optionally it can be installed in development mode, so you can modify the original files without having to reinstall the package between edits. It can be done with 
```shell script
python setup.py develop
```
instead of the normal installation command.
