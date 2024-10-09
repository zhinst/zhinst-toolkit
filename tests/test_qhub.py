from itertools import cycle
import pytest

from zhinst.toolkit.driver.devices.qhub import QHub
from zhinst.toolkit.exceptions import ToolkitError


@pytest.fixture()
def qhub(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_qhub.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json
    mock_connection.return_value.getString.return_value = ""

    yield QHub("DEV1234", "QHUB", session)


def test_repr(qhub):
    assert repr(qhub) == "QHub(QHUB,DEV1234)"


def test_arm(mock_connection, qhub):
    qhub.arm()
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/execution/enable", False
    )

    qhub.arm(repetitions=3, holdoff=100.6)
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/execution/enable", False
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/repetitions", 3
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/holdoff", 100.6
    )

    qhub.arm(deep=False, repetitions=5, holdoff=67.4)
    mock_connection.return_value.set.assert_any_call("/dev1234/execution/enable", False)
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/repetitions", 5
    )
    mock_connection.return_value.set.assert_any_call("/dev1234/execution/holdoff", 67.4)


def test_run_stop(mock_connection, qhub):
    qhub.run(deep=False)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/execution/enable", True
    )
    qhub.run()
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/execution/enable", True
    )

    qhub.stop(deep=False)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/execution/enable", False
    )
    qhub.stop()
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/execution/enable", False
    )
    mock_connection.reset_mock()

    qhub.arm_and_run(repetitions=5, holdoff=100.8)
    mock_connection.return_value.syncSetInt.assert_any_call(
        "/dev1234/execution/enable", False
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/repetitions", 5
    )
    mock_connection.return_value.set.assert_any_call(
        "/dev1234/execution/holdoff", 100.8
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/execution/enable", True
    )


def test_wait_done(mock_connection, qhub):
    sequence = iter([1] * 3 + [0] * 5)
    mock_connection.return_value.getInt.side_effect = lambda node: next(sequence)
    mock_connection.return_value.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [next(sequence)]}
    }
    qhub.wait_done(sleep_time=0.001)
    mock_connection.return_value.getInt.assert_called_with("/dev1234/execution/enable")

    mock_connection.return_value.getInt.side_effect = lambda node: 1
    mock_connection.return_value.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e_info:
        qhub.wait_done(timeout=0.01)
    mock_connection.return_value.getInt.assert_called_with("/dev1234/execution/enable")


def test_ref_clock(mock_connection, qhub):

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

    assert qhub.check_ref_clock(sleep_time=0.001)
    # Locked within time
    status = iter([2] * 2 + [0] * 10)
    assert qhub.check_ref_clock(sleep_time=0.001)
    # Locking error but actual_clock == clock
    status = cycle([1])
    assert not qhub.check_ref_clock(sleep_time=0.001)
    # Locking error and actual_clock != clock => reset clock to internal
    source = 1
    mock_connection.return_value.syncSetString.assert_not_called()
    assert not qhub.check_ref_clock(sleep_time=0.001)
    mock_connection.return_value.syncSetString.assert_called_with(
        "/dev1234/system/clocks/referenceclock/in/source", "internal"
    )

    # timeout
    status = cycle([2])
    with pytest.raises(TimeoutError) as e_info:
        qhub.check_ref_clock(timeout=0.01, sleep_time=0.001)


def test_check_zsync_connection(mock_connection, qhub, shfqa, shfsg, shfqc):

    # hijack serials of instruments
    shfsg._serial = "dev1111"  # port 0
    shfqa._serial = "dev2222"  # port 2
    shfqc._serial = "dev3333"  # port 10

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

    def get_serials(path):
        # assume it ask for path "/dev1234/zsyncs/*/connection/serial"
        return_dict = {}
        for port in range(18):
            key = f"/dev1234/zsyncs/{port:d}/connection/serial"
            if port == 0 and status0 != 0:
                serial = "1111"
            elif port == 2 and status2 != 0:
                serial = "2222"
            elif port == 10 and status10 != 0:
                serial = "3333"
            else:
                serial = ""

            return_dict[key] = [{"timestamp": 0, "flags": 0, "vector": serial}]

        return return_dict

    def get_side_effect(path, **kwargs):
        if path.endswith("status"):
            value = getInt_side_effect(path)
            return {path: {"timestamp": [0], "value": [value]}}
        elif path.endswith("serial"):
            return get_serials(path)
        else:
            return None

    mock_connection.return_value.getInt.side_effect = getInt_side_effect
    mock_connection.return_value.get.side_effect = get_side_effect

    # not connected
    with pytest.raises(TimeoutError):
        qhub.check_zsync_connection(0, timeout=0, sleep_time=0.001)
    with pytest.raises(TimeoutError):
        qhub.check_zsync_connection(2, timeout=0, sleep_time=0.001)
    with pytest.raises(TimeoutError):
        qhub.check_zsync_connection([0], timeout=0, sleep_time=0.001)
    with pytest.raises(TimeoutError):
        qhub.check_zsync_connection([0, 2], timeout=0, sleep_time=0.001)

    # one connected
    status0 = 2
    assert True == qhub.check_zsync_connection(0)
    with pytest.raises(TimeoutError):
        qhub.check_zsync_connection(2, timeout=0, sleep_time=0.001)
    assert [True] == qhub.check_zsync_connection([0])
    with pytest.raises(TimeoutError):
        qhub.check_zsync_connection([0, 2], timeout=0, sleep_time=0.001)

    # one connected the other one in error state
    status0 = 2
    status2 = 3
    assert True == qhub.check_zsync_connection(0, sleep_time=0.001)
    with pytest.raises(TimeoutError) as e_info:
        qhub.check_zsync_connection(2, timeout=0.01)
    assert [True] == qhub.check_zsync_connection([0], sleep_time=0.001)

    with pytest.raises(TimeoutError) as e_info:
        qhub.check_zsync_connection([0, 2], timeout=0.01, sleep_time=0.001)
    assert "2" in str(e_info.value)

    # one connected the other one times out
    status0 = 2
    status2 = 1
    assert True == qhub.check_zsync_connection(0, sleep_time=0.001)
    with pytest.raises(TimeoutError) as e_info:
        qhub.check_zsync_connection(2, timeout=0.01)
    assert [True] == qhub.check_zsync_connection([0], sleep_time=0.001)

    with pytest.raises(TimeoutError) as e_info:
        qhub.check_zsync_connection([0, 2], timeout=0.01, sleep_time=0.001)
    assert "2" in str(e_info.value)

    # test two decimal place value
    status10 = 2
    status0 = 2
    status2 = 3
    assert [True] == qhub.check_zsync_connection([10], sleep_time=0.001)
    with pytest.raises(TimeoutError) as e_info:
        qhub.check_zsync_connection([0, 2, 10], timeout=0.01, sleep_time=0.001)
    assert "2" in str(e_info.value)

    # Test with instruments
    status0 = 2
    status2 = 2

    assert True == qhub.check_zsync_connection(shfsg, timeout=0.05, sleep_time=0.001)
    assert True == qhub.check_zsync_connection(shfqa, timeout=0.05, sleep_time=0.001)
    assert [True, True] == qhub.check_zsync_connection(
        [shfsg, shfqa], timeout=0.05, sleep_time=0.001
    )

    status10 = 3
    with pytest.raises(TimeoutError) as e_info:
        qhub.check_zsync_connection(shfqc, timeout=0.05, sleep_time=0.001)

    status10 = 0
    with pytest.raises(ToolkitError) as e_info:
        qhub.check_zsync_connection(shfqc, timeout=0.05, sleep_time=0.001)


def test_find_zsync_worker_port(mock_connection, qhub):
    # device not connected
    ret_val = {"random/path": [{"timestamp": 0, "flags": 0, "vector": ""}]}
    mock_connection.return_value.get.return_value = ret_val
    with pytest.raises(RuntimeError):
        qhub.find_zsync_worker_port(qhub)

    # correct use case
    ret_val = {
        "/dev1234/zsyncs/0/connection/serial": [
            {"timestamp": 0, "flags": 0, "vector": "1234"}
        ]
    }
    mock_connection.return_value.get.return_value = ret_val
    assert qhub.find_zsync_worker_port(qhub) == 0
