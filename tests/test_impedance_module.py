import pytest
from itertools import cycle

from zhinst.toolkit.driver.modules.impedance_module import (
    ImpedanceModule,
    CalibrationStatus,
)


@pytest.fixture()
def impedance_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_impedance_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.impedanceModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield ImpedanceModule(mock_connection.return_value.impedanceModule(), session)


def test_repr(impedance_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(impedance_module)


def test_wait_done(impedance_module):
    calibrate = 1
    status = cycle([1])
    expectedstatus = 1

    def getInt(node, *args, **kwargs):
        if node == "/calibrate":
            return calibrate
        if node == "/status":
            return next(status)
        if node == "/expectedstatus":
            return expectedstatus
        raise RuntimeError("Node not found")

    impedance_module.raw_module.getInt.side_effect = getInt
    impedance_module.raw_module.progress.return_value = [1]
    impedance_module.wait_done()

    # waiting a moment
    status = cycle([0, 0, 0, 1, 1, 1])
    impedance_module.wait_done(sleep_time=0.001)


def test_wait_done_timeout(impedance_module):
    impedance_module.raw_module.getInt.return_value = 0
    impedance_module.raw_module.progress.return_value = [0]
    with pytest.raises(TimeoutError):
        impedance_module.wait_done()


def test_wait_done_fail(impedance_module):
    calibrate = 0
    status = 2
    expectedstatus = 1

    def getInt(node, *args, **kwargs):
        if node == "/calibrate":
            return calibrate
        if node == "/status":
            return status
        if node == "/expectedstatus":
            return expectedstatus
        raise RuntimeError("Node not found")

    impedance_module.raw_module.getInt.side_effect = getInt
    impedance_module.raw_module.progress.return_value = [1]
    with pytest.raises(RuntimeError):
        impedance_module.wait_done()


def test_wait_done_fail_stage(impedance_module):
    calibrate = 0
    status = 2
    expectedstatus = 1

    def getInt(node, *args, **kwargs):
        if node == "/calibrate":
            return calibrate
        if node == "/status":
            return status
        if node == "/expectedstatus":
            return expectedstatus
        raise RuntimeError("Node not found")

    impedance_module.raw_module.getInt.side_effect = getInt
    impedance_module.raw_module.progress.return_value = [1]
    with pytest.raises(RuntimeError):
        impedance_module.wait_done(4)


def test_finish(impedance_module):
    impedance_module.finish()
    impedance_module.raw_module.finish.assert_called_once()


def test_finished(impedance_module):
    impedance_module.raw_module.getInt.side_effect = [1, 1]
    assert impedance_module.finished()

    impedance_module.raw_module.getInt.side_effect = [3, 3]
    assert impedance_module.finished()

    impedance_module.raw_module.getInt.side_effect = [3, 1]
    assert not impedance_module.finished()


def test_finished_step(impedance_module):
    impedance_module.raw_module.getInt.return_value = 1
    assert impedance_module.finished(0)

    assert not impedance_module.finished(1)
    impedance_module.raw_module.getInt.return_value = 3
    assert impedance_module.finished(1)


def test_progress(impedance_module):
    impedance_module.progress()
    impedance_module.raw_module.progress.assert_called_once()


def test_calibrate_status_repr():
    assert (
        repr(CalibrationStatus(13))
        == "step 0: True, step 1: False, step 2: True, step 3: True"
    )
    assert repr(CalibrationStatus(0)) == ""
    assert repr(CalibrationStatus(5)) == "step 0: True, step 1: False, step 2: True"


def test_calibrate_status_item():
    status = CalibrationStatus(13)
    assert status[0] == 1
    assert status[1] == 0
    assert status[2] == 1
    assert status[3] == 1
    assert status[4] == 0
    assert status[5] == 0


def test_calibrate_status_len():
    assert len(CalibrationStatus(13)) == 4
    assert len(CalibrationStatus(0)) == 0
    assert len(CalibrationStatus(2)) == 2
    assert len(CalibrationStatus(5)) == 3
