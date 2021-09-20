# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""The Zurich Instruments Toolkit (zhinst-toolkit)

This package is a collection of Python tools for high level device
control. Based on the native interface to Zurich Instruments LabOne,
they offer an easy and user-friendly way to control Zurich Instruments
devices. It  is tailored to control multiple instruments together,
especially for device management and multiple AWG distributed control.

The Toolkit forms the basis for instrument drivers used in QCoDeS and
Labber. It comes in the form of a package compatible with Python 3.6+.
"""

from zhinst.toolkit.control.drivers import (
    BaseInstrument,
    HDAWG,
    UHFQA,
    UHFLI,
    MFLI,
    PQSC,
    SHFQA,
    SHFSG,
)
from zhinst.toolkit.interface import DeviceTypes
from zhinst.toolkit.control.multi_device_connection import MultiDeviceConnection
from zhinst.toolkit.helpers.utils import SequenceType, TriggerMode, Alignment
from zhinst.toolkit._version import version as __version__
