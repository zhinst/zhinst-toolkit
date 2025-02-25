# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""The Zurich Instruments Toolkit (zhinst-toolkit).

This package is a collection of Python tools for high level device
control. Based on the native interface to Zurich Instruments LabOne,
they offer an easy and user-friendly way to control Zurich Instruments
devices. It  is tailored to control multiple instruments together,
especially for device management and multiple AWG distributed control.
"""
from zhinst.toolkit.command_table import CommandTable
from zhinst.toolkit.driver.modules.pid_advisor_module import PIDMode
from zhinst.toolkit.interface import AveragingMode, SHFQAChannelMode
from zhinst.toolkit.sequence import Sequence
from zhinst.toolkit.session import PollFlags, Session
from zhinst.toolkit.waveform import Waveforms

try:
    from zhinst.toolkit._version import version as __version__
except ModuleNotFoundError:  # pragma: no cover
    pass

__all__ = [
    "AveragingMode",
    "CommandTable",
    "PIDMode",
    "PollFlags",
    "SHFQAChannelMode",
    "Sequence",
    "Session",
    "Waveforms",
    "__version__",
]
