from itertools import cycle

import pytest


def shf_test_ref_clock(mock_connection, shf):
    """Test reference clock logic shared between all SHF devices."""
    status = cycle([0])
    source = 0
    source_actual = 0

    def getInt_side_effect(path):
        if path == "/dev1234/system/clocks/referenceclock/in/status":
            return next(status)
        if path == "/dev1234/system/clocks/referenceclock/in/source":
            return source
        if path == "/dev1234/system/clocks/referenceclock/in/sourceactual":
            return source_actual
        raise RuntimeError("Invalid Node")

    def get_side_effect(path, **kwargs):
        value = getInt_side_effect(path)
        return {path: {"timestamp": [0], "value": [value]}}

    mock_connection.return_value.getInt.side_effect = getInt_side_effect
    mock_connection.return_value.get.side_effect = get_side_effect

    assert shf.check_ref_clock(sleep_time=0.001)
    # Locked within time
    status = iter([2] * 2 + [0] * 10)
    assert shf.check_ref_clock(sleep_time=0.001)
    # Locking error but actual_clock == clock
    status = cycle([1])
    assert not shf.check_ref_clock(sleep_time=0.001)
    # Locking error and actual_clock != clock => reset clock to internal
    source = 1
    mock_connection.return_value.syncSetString.assert_not_called()
    assert not shf.check_ref_clock(sleep_time=0.001)
    mock_connection.return_value.syncSetString.assert_called_with(
        "/dev1234/system/clocks/referenceclock/in/source", "internal"
    )

    # timeout
    status = cycle([2])
    with pytest.raises(TimeoutError) as e_info:
        shf.check_ref_clock(timeout=0.01, sleep_time=0.001)
