from collections import OrderedDict
from itertools import cycle
from socket import timeout

import numpy as np
import pytest

from zhinst.toolkit.driver.devices.pqsc import PQSC


@pytest.fixture()
def pqsc(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_pqsc.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json
    mock_connection.return_value.getString.return_value = ""

    yield PQSC("DEV1234", "PQSC", session)


def test_repr(pqsc):
    assert repr(pqsc) == "PQSC(PQSC,DEV1234)"


def test_arm(mock_connection, pqsc):
    pqsc.arm()
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/execution/enable", False
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/feedback/registerbank/reset", 1
    )

    pqsc.arm(repetitions=3, holdoff=100.6)
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/execution/enable", False
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/repetitions", 3
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/holdoff", 100.6
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/feedback/registerbank/reset", 1
    )

    pqsc.arm(deep=False, repetitions=5, holdoff=67.4)
    mock_connection.return_value.set.assert_any_call("/dev1234/execution/enable", False)
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/repetitions", 5
    )
    mock_connection.return_value.set.assert_any_call("/dev1234/execution/holdoff", 67.4)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/feedback/registerbank/reset", 1
    )


def test_run_stop(mock_connection, pqsc):
    pqsc.run(deep=False)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/execution/enable", True
    )
    pqsc.run()
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/execution/enable", True
    )

    pqsc.stop(deep=False)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/execution/enable", False
    )
    pqsc.stop()
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/execution/enable", False
    )
    mock_connection.reset_mock()

    pqsc.arm_and_run(repetitions=5, holdoff=100.8)
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/execution/enable", False
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/repetitions", 5
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/holdoff", 100.8
    )
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/feedback/registerbank/reset", 1
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/execution/enable", True
    )


def test_wait_done(mock_connection, pqsc):
    mock_connection.return_value.getInt.side_effect = [1, 1, 1, 0, 0, 0, 0, 0]
    pqsc.wait_done()
    mock_connection.return_value.getInt.assert_called_with("/dev1234/execution/enable")

    mock_connection.return_value.getInt.side_effect = None
    mock_connection.return_value.getInt.return_value = 1
    with pytest.raises(TimeoutError) as e_info:
        pqsc.wait_done(timeout=0.2)
    mock_connection.return_value.getInt.assert_called_with("/dev1234/execution/enable")


def test_ref_clock(mock_connection, pqsc):

    status = cycle([0])
    source = 0
    source_actual = 0

    def get_side_effect(path):
        if path == "/dev1234/system/clocks/referenceclock/in/status":
            return next(status)
        if path == "/dev1234/system/clocks/referenceclock/in/source":
            return source
        if path == "/dev1234/system/clocks/referenceclock/in/sourceactual":
            return source_actual
        raise RuntimeError("Invalid Node")

    mock_connection.return_value.getInt.side_effect = get_side_effect

    assert pqsc.check_ref_clock()
    # Locked within time
    status = iter([2] * 2 + [0] * 10)
    assert pqsc.check_ref_clock()
    # Locking error but actual_clock == clock
    status = cycle([1])
    assert not pqsc.check_ref_clock()
    # Locking error and actual_clock != clock => reset clock to internal
    source = 1
    mock_connection.return_value.syncSetString.assert_not_called()
    assert not pqsc.check_ref_clock()
    mock_connection.return_value.syncSetString.assert_called_with(
        "/dev1234/system/clocks/referenceclock/in/source", "internal"
    )

    # timeout
    status = cycle([2])
    with pytest.raises(TimeoutError) as e_info:
        pqsc.check_ref_clock(timeout=0.2)


def test_check_zsync_connection(mock_connection, pqsc):

    cycle([2])

    status0 = 0
    status2 = 0
    status10 = 0

    def getInt_side_effect(path):
        if path == "/dev1234/zsyncs/0/connection/status":
            return status0
        if path == "/dev1234/zsyncs/2/connection/status":
            return status2
        if path == "/dev1234/zsyncs/10/connection/status":
            return status10
        raise RuntimeError("Invalid Node")

    mock_connection.return_value.getInt.side_effect = getInt_side_effect

    # not connected
    with pytest.raises(TimeoutError):
        pqsc.check_zsync_connection(timeout=0)
    with pytest.raises(TimeoutError):
        pqsc.check_zsync_connection(2, timeout=0)
    with pytest.raises(TimeoutError):
        pqsc.check_zsync_connection([0], timeout=0)
    with pytest.raises(TimeoutError):
        pqsc.check_zsync_connection([0, 2], timeout=0)

    # one connected
    status0 = 2
    assert True == pqsc.check_zsync_connection()
    with pytest.raises(TimeoutError):
        pqsc.check_zsync_connection(2, timeout=0)
    assert [True] == pqsc.check_zsync_connection([0])
    with pytest.raises(TimeoutError):
        pqsc.check_zsync_connection([0, 2], timeout=0)

    # one connected the other one in error state
    status0 = 2
    status2 = 3
    assert True == pqsc.check_zsync_connection()
    assert False == pqsc.check_zsync_connection(2)
    assert [True] == pqsc.check_zsync_connection([0])
    assert [True, False] == pqsc.check_zsync_connection([0, 2])

    # one connected the other one times out
    status0 = 2
    status2 = 1
    assert True == pqsc.check_zsync_connection()
    with pytest.raises(TimeoutError) as e_info:
        pqsc.check_zsync_connection(2, timeout=0.01)
    assert [True] == pqsc.check_zsync_connection([0])

    with pytest.raises(TimeoutError) as e_info:
        pqsc.check_zsync_connection([0, 2], timeout=0.01)
    assert "2" in str(e_info.value)

    # test two decimal place value
    status10 = 2
    status0 = 2
    status2 = 3
    assert [True] == pqsc.check_zsync_connection([10])
    assert [True, False, True] == pqsc.check_zsync_connection([0, 2, 10])
