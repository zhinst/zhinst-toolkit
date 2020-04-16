# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from enum import Enum


class SequenceType(Enum):
    NONE = None
    SIMPLE = "Simple"
    RABI = "Rabi"
    T1 = "T1"
    T2 = "T2*"
    READOUT = "Readout"
    PULSED_SPEC = "Pulsed Spectroscopy"
    CW_SPEC = "CW Spectroscopy"
    CUSTOM = "Custom"
    TRIGGER = "Trigger"


class TriggerMode(Enum):
    NONE = None
    SEND_TRIGGER = "Send Trigger"
    EXTERNAL_TRIGGER = "External Trigger"


class Alignment(Enum):
    START_WITH_TRIGGER = "Start with Trigger"
    END_WITH_TRIGGER = "End with Trigger"
