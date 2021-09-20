import pytest
from hypothesis import given, strategies as st

from .context import (
    SHFSG,
    SHFSG_Channel,
    DeviceTypes,
    SequenceType,
    TriggerMode,
    shfsg_logger,
)

shfsg_logger.disable_logging()


def test_init_shfsg():
    shf = SHFSG("name", "dev12000")
    assert len(shf._sgchannels) == 0
    assert len(shf.sgchannels) == 0
    assert shf.device_type == DeviceTypes.SHFSG
    assert shf.ref_clock is None
    assert shf.ref_clock_status is None
    assert shf.allowed_sequences == [
        SequenceType.NONE,
        SequenceType.SIMPLE,
        SequenceType.TRIGGER,
        SequenceType.RABI,
        SequenceType.T1,
        SequenceType.T2,
        SequenceType.CUSTOM,
    ]
    assert shf.allowed_trigger_modes == [
        TriggerMode.NONE,
        TriggerMode.SEND_TRIGGER,
        TriggerMode.EXTERNAL_TRIGGER,
        TriggerMode.RECEIVE_TRIGGER,
        TriggerMode.SEND_AND_RECEIVE_TRIGGER,
        TriggerMode.ZSYNC_TRIGGER,
    ]
    with pytest.raises(shfsg_logger.ToolkitConnectionError):
        shf._init_sgchannels()
    with pytest.raises(shfsg_logger.ToolkitConnectionError):
        shf._init_params()
    shf._init_settings()


def test_methods_shfsg():
    shf = SHFSG("name", "dev12000")
    with pytest.raises(shfsg_logger.ToolkitConnectionError):
        shf.connect_device()
    # with pytest.raises(shfsg_logger.ToolkitConnectionError):
    #     shf.factory_reset()
    with pytest.raises(shfsg_logger.ToolkitConnectionError):
        shf.enable_qccs_mode()
    with pytest.raises(shfsg_logger.ToolkitConnectionError):
        shf.enable_manual_mode()
