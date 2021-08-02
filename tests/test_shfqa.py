# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest

from .context import (
    SHFQA,
    SHFQA_Channel,
    SHFQA_Generator,
    SHFQA_Sweeper,
    SHFQA_Scope,
    DeviceTypes,
    SequenceType,
    TriggerMode,
    shfqa_logger,
)

shfqa_logger.disable_logging()


def test_init_shfqa():
    qa = SHFQA("name", "dev12000")
    assert qa.device_type == DeviceTypes.SHFQA
    assert len(qa._qachannels) == 0
    assert len(qa.qachannels) == 0
    assert qa._scope is None
    assert qa.scope is None
    assert qa.ref_clock is None
    assert qa.ref_clock_actual is None
    assert qa.ref_clock_status is None
    assert qa.allowed_sequences == [
        SequenceType.NONE,
        SequenceType.CUSTOM,
    ]
    assert qa.allowed_trigger_modes == [
        TriggerMode.NONE,
        TriggerMode.RECEIVE_TRIGGER,
        TriggerMode.ZSYNC_TRIGGER,
    ]
    with pytest.raises(shfqa_logger.ToolkitConnectionError):
        qa._init_qachannels()
    with pytest.raises(shfqa_logger.ToolkitConnectionError):
        qa._init_scope()
    with pytest.raises(shfqa_logger.ToolkitConnectionError):
        qa._init_params()
    qa._init_settings()
