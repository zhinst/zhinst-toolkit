import numpy as np
import pytest

from zhinst.toolkit.driver.modules.pid_advisor_module import PIDAdvisorModule, PIDMode


@pytest.fixture()
def pid_advisor_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_pid_advisor_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.pidAdvisor.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield PIDAdvisorModule(mock_connection.return_value.pidAdvisor(), session)


def test_repr(pid_advisor_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(pid_advisor_module)


def test_pid_mode_node(pid_advisor_module):
    pid_advisor_module.raw_module.getInt.return_value = 0
    assert pid_advisor_module.pid.mode() == PIDMode.NONE

    pid_advisor_module.raw_module.getInt.return_value = 1
    assert pid_advisor_module.pid.mode() == PIDMode.P_Gain

    pid_advisor_module.raw_module.getInt.return_value = 2
    assert pid_advisor_module.pid.mode() == PIDMode.I_Gain

    pid_advisor_module.raw_module.getInt.return_value = 4
    assert pid_advisor_module.pid.mode() == PIDMode.D_Gain

    pid_advisor_module.raw_module.getInt.return_value = 8
    assert pid_advisor_module.pid.mode() == PIDMode.D_Filter_Limit

    pid_advisor_module.raw_module.getInt.return_value = 15
    assert (
        pid_advisor_module.pid.mode()
        == PIDMode.P_Gain | PIDMode.I_Gain | PIDMode.D_Gain | PIDMode.D_Filter_Limit
    )


def test_tuner_mode_node(pid_advisor_module):
    pid_advisor_module.raw_module.getInt.return_value = 0
    assert pid_advisor_module.tuner.mode() == PIDMode.NONE

    pid_advisor_module.raw_module.getInt.return_value = 1
    assert pid_advisor_module.tuner.mode() == PIDMode.P_Gain

    pid_advisor_module.raw_module.getInt.return_value = 2
    assert pid_advisor_module.tuner.mode() == PIDMode.I_Gain

    pid_advisor_module.raw_module.getInt.return_value = 4
    assert pid_advisor_module.tuner.mode() == PIDMode.D_Gain

    pid_advisor_module.raw_module.getInt.return_value = 8
    assert pid_advisor_module.tuner.mode() == PIDMode.D_Filter_Limit

    pid_advisor_module.raw_module.getInt.return_value = 15
    assert (
        pid_advisor_module.tuner.mode()
        == PIDMode.P_Gain | PIDMode.I_Gain | PIDMode.D_Gain | PIDMode.D_Filter_Limit
    )


def test_wait_done(pid_advisor_module):
    pid_advisor_module.raw_module.getInt.return_value = 0
    pid_advisor_module.raw_module.finished.return_value = 1
    pid_advisor_module.raw_module.progress.return_value = np.array([1])
    pid_advisor_module.wait_done()

    pid_advisor_module.raw_module.getInt.return_value = 1
    with pytest.raises(TimeoutError):
        pid_advisor_module.wait_done(timeout=0.01, sleep_time=0.001)

    pid_advisor_module.raw_module.getInt.return_value = 1
    pid_advisor_module.raw_module.progress.return_value = np.array([1])
    with pytest.raises(TimeoutError):
        pid_advisor_module.wait_done(timeout=0.01, sleep_time=0.001)

    pid_advisor_module.raw_module.finished.return_value = 0
    pid_advisor_module.raw_module.progress.return_value = np.array([0.1])
    with pytest.raises(TimeoutError):
        pid_advisor_module.wait_done(timeout=0.01, sleep_time=0.001)
