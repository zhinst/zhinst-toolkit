# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from enum import Enum


class SequenceType(Enum):
    """Enums for the `sequence_type` sequence parameter.

    Can be used as inputs to the `set_sequence_params(...)` method of the AWG
    Cores. For example like this:

        >>> from zhinst.toolkit import SequenceType
        >>> ...
        >>> uhfqa.awg.set_sequence_params(
        >>>     sequence_type=SequenceType.READOUT,
        >>>     ...
        >>> )

    """

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
    """Enums for the `trigger_mode` sequence parameter.

    Can be used as inputs to the `set_seuqence_params(...)` method of the AWG
    Cores. For example like this:

        >>> from zhinst.toolkit import TriggerMode
        >>> ...
        >>> uhfqa.awg.set_sequence_params(
        >>>     trigger_mode=TriggerMode.SEND_TRIGGER,
        >>>     ...
        >>> )

    """

    NONE = None
    SEND_TRIGGER = "Send Trigger"
    EXTERNAL_TRIGGER = "External Trigger"  # deprecated
    RECEIVE_TRIGGER = "Receive Trigger"
    SEND_AND_RECEIVE_TRIGGER = "Send and Receive Trigger"
    ZSYNC_TRIGGER = "ZSync Trigger"


class Alignment(Enum):
    """Enums for the `alignment` sequence parameter.

    Can be used as inputs to the `set_seuqence_params(...)` method of the AWG
    Cores. For example like this:

        >>> from zhinst.toolkit import Alignment
        >>> ...
        >>> uhfqa.awg.set_sequence_params(
        >>>     alignment=Alignment.START_WITH_TRIGGER,
        >>>     ...
        >>> )

    """

    START_WITH_TRIGGER = "Start with Trigger"
    END_WITH_TRIGGER = "End with Trigger"
