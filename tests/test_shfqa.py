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
    ToolkitError,
)


def test_init_shfqa():
    qa = SHFQA("name", "dev12000")
    assert qa.device_type == DeviceTypes.SHFQA
    assert len(qa._channels) == 0
    assert len(qa.channels) == 0
    assert qa._scope is None
    assert qa.scope is None
    assert qa.ref_clock is None
    assert qa.ref_clock_actual is None
    assert qa.ref_clock_status is None
    assert qa.timebase is None
    assert qa.allowed_sequences == [
        SequenceType.NONE,
        SequenceType.CUSTOM,
    ]
    assert qa.allowed_trigger_modes == [
        TriggerMode.NONE,
    ]
    with pytest.raises(AttributeError):
        qa._init_channels()
    with pytest.raises(TypeError):
        qa._init_scope()
    with pytest.raises(ToolkitError):
        qa._init_params()
    qa._init_settings()
