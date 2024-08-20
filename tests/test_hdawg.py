from itertools import cycle
import re
from unittest.mock import patch

import pytest

from zhinst.toolkit.driver.devices.hdawg import AWG, HDAWG
from zhinst.toolkit.exceptions import ToolkitError
from zhinst.toolkit.nodetree import Node


@pytest.fixture
def hdawg(data_dir, mock_connection, session):

    json_path = data_dir / "nodedoc_dev1234_hdawg.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.listNodesJSON.return_value = nodes_json

    mock_connection.return_value.listNodes.return_value = [
        "/dev1234/awgs/0",
        "/dev1234/awgs/1",
        "/dev1234/awgs/2",
        "/dev1234/awgs/3",
    ]
    mock_connection.return_value.getString.return_value = ""

    return HDAWG("DEV1234", "HDAWG4", session)


def test_repr(hdawg):
    assert repr(hdawg) == "HDAWG(HDAWG4,DEV1234)"


def test_enable_qccs_mode(mock_connection, hdawg):
    # No argument, equal to gen1
    hdawg.enable_qccs_mode()
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/dios/0/mode", "qccs"),
            ("/dev1234/system/clocks/sampleclock/freq", 2.4e9),
            ("/dev1234/dios/0/interface", 0),
            ("/dev1234/dios/0/drive", 12),
            ("/dev1234/system/clocks/referenceclock/source", "zsync"),
            ("/dev1234/awgs/*/dio/strobe/slope", "off"),
            ("/dev1234/awgs/*/dio/valid/polarity", "none"),
        ],
    )

    # Set transaction check
    mock_connection.reset_mock()
    with hdawg.set_transaction():
        hdawg.enable_qccs_mode()
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/dios/0/mode", "qccs"),
            ("/dev1234/system/clocks/sampleclock/freq", 2.4e9),
            ("/dev1234/dios/0/interface", 0),
            ("/dev1234/dios/0/drive", 12),
            ("/dev1234/system/clocks/referenceclock/source", "zsync"),
            ("/dev1234/awgs/*/dio/strobe/slope", "off"),
            ("/dev1234/awgs/*/dio/valid/polarity", "none"),
        ],
    )

    # Gen1 test
    mock_connection.reset_mock()
    hdawg.enable_qccs_mode(gen=1)
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/dios/0/mode", "qccs"),
            ("/dev1234/system/clocks/sampleclock/freq", 2.4e9),
            ("/dev1234/dios/0/interface", 0),
            ("/dev1234/dios/0/drive", 12),
            ("/dev1234/system/clocks/referenceclock/source", "zsync"),
            ("/dev1234/awgs/*/dio/strobe/slope", "off"),
            ("/dev1234/awgs/*/dio/valid/polarity", "none"),
        ],
    )

    # Gen2 test
    mock_connection.reset_mock()
    hdawg.enable_qccs_mode(gen=2)
    mock_connection.return_value.set.assert_called_with(
        [
            ("/dev1234/dios/0/mode", "qccs"),
            ("/dev1234/system/clocks/sampleclock/freq", 2.0e9),
            ("/dev1234/dios/0/drive", 0),
            ("/dev1234/system/clocks/referenceclock/source", "zsync"),
            ("/dev1234/awgs/*/dio/strobe/slope", "off"),
            ("/dev1234/awgs/*/dio/valid/polarity", "none"),
        ],
    )

    # wrong argument
    mock_connection.reset_mock()
    with pytest.raises(ToolkitError):
        hdawg.enable_qccs_mode(gen=1234)


def test_awg(hdawg):
    assert len(hdawg.awgs) == 4
    assert isinstance(hdawg.awgs[0], AWG)
    # Wildcards nodes will be converted into normal Nodes
    assert not isinstance(hdawg.awgs["*"], AWG)
    assert isinstance(hdawg.awgs["*"], Node)


def test_awg_compiler(mock_connection, hdawg):
    mock_connection.return_value.getString.return_value = "AWG,FOOBAR"
    mock_connection.return_value.getDouble.return_value = 10000
    with patch(
        "zhinst.toolkit.driver.nodes.awg.compile_seqc",
        autospec=True,
    ) as compile_seqc:
        hdawg.awgs[0].compile_sequencer_program("test")
        compile_seqc.assert_called_once_with(
            "test",
            "HDAWG4",
            "AWG,FOOBAR",
            0,
            samplerate=10000,
        )
        compile_seqc.reset_mock()
        hdawg.awgs[1].compile_sequencer_program("test")
        compile_seqc.assert_called_once_with(
            "test",
            "HDAWG4",
            "AWG,FOOBAR",
            1,
            samplerate=10000,
        )


def test_ref_clock_hdawg(mock_connection, hdawg):
    """Test reference clock logic of HDAWG"""
    # Note: When the source actual node is introduced on HDAWG, this test should be removed
    #       and HDAWG support should be added to the test shf_test_ref_clock (and that test
    #       should then be renamed).
    status = cycle([0])
    source = cycle([1])
    sigout_busy = cycle([0])

    def getInt_side_effect(path):
        if path == "/dev1234/system/clocks/referenceclock/status":
            return next(status)
        if path == "/dev1234/system/clocks/referenceclock/source":
            return source
        if re.match(r"^/dev1234/sigouts/(\d+|\*)/busy$", path):
            return next(sigout_busy)
        raise RuntimeError("Invalid Node")

    def get_side_effect(path, **kwargs):
        value = getInt_side_effect(path)
        return {path: {"timestamp": [0], "value": [value]}}

    mock_connection.return_value.getInt.side_effect = getInt_side_effect
    mock_connection.return_value.get.side_effect = get_side_effect

    assert hdawg.check_ref_clock(sleep_time=0.001)
    # Locked within time
    status = iter([2] * 2 + [0] * 10)
    sigout_busy = iter([1] * 2 + [0] * 10)
    assert hdawg.check_ref_clock(sleep_time=0.001)

    # Locked within time, but channel stays busy too long
    status = iter([2] * 2 + [0] * 10)
    sigout_busy = cycle([1])
    with pytest.raises(TimeoutError) as _:
        hdawg.check_ref_clock(sleep_time=0.001)

    # Locking error but actual_clock == clock
    status = cycle([1])
    assert not hdawg.check_ref_clock(sleep_time=0.001)

    # timeout
    status = cycle([2])
    with pytest.raises(TimeoutError) as _:
        hdawg.check_ref_clock(timeout=0.01, sleep_time=0.001)
