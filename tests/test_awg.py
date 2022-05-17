import json
from collections import OrderedDict
from itertools import cycle

import numpy as np
import pytest
import zhinst.utils as zi_utils

from zhinst.toolkit.driver.nodes.awg import CommandTableNode, Waveforms


@pytest.fixture()
def awg_module(shfsg, data_dir, mock_connection):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield shfsg.sgchannels[0].awg


@pytest.fixture()
def awg_module_qc(shfqc, data_dir, mock_connection):
    json_path = data_dir / "nodedoc_awg_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.awgModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield shfqc.sgchannels[0].awg


@pytest.fixture()
def waveform_descriptors_json(data_dir):
    json_path = data_dir / "waveform_descriptors.json"
    with json_path.open("r", encoding="UTF-8") as file:
        return file.read()


def test_enable_sequencer(mock_connection, awg_module):
    awg_module.enable_sequencer(single=True)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/sgchannels/0/awg/single", 1
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/sgchannels/0/awg/enable", 1
    )

    awg_module.enable_sequencer(single=False)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/sgchannels/0/awg/single", 0
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/sgchannels/0/awg/enable", 1
    )


def test_wait_done(mock_connection, awg_module):
    single = 0
    enable = iter([])

    def get_int_side_effect(node):
        if node.upper() == "/DEV1234/SGCHANNELS/0/AWG/SINGLE":
            return single
        if node.upper() == "/DEV1234/SGCHANNELS/0/AWG/ENABLE":
            return next(enable)

    mock_connection.return_value.getInt.side_effect = get_int_side_effect

    # if not single mode this function throws a RuntimeError
    with pytest.raises(RuntimeError) as e_info:
        awg_module.wait_done()

    # already finished
    single = 1
    enable = iter([0] * 2)
    awg_module.wait_done()
    # finishes in time
    single = 1
    enable = iter([1] * 3 + [0] * 2)
    awg_module.wait_done()
    # don't finish
    single = 1
    enable = cycle([1])
    with pytest.raises(TimeoutError) as e_info:
        awg_module.wait_done(timeout=0.1)


def test_load_sequencer_program(mock_connection, awg_module, caplog):
    compiler_status = 0
    upload_process = iter([0, 0.2, 1, 1])
    ready = 1
    elf_status = 0

    def get_side_effect(node):
        if node == "/compiler/status":
            return compiler_status
        if node == "/progress":
            return next(upload_process)
        if node == "/elf/status":
            return elf_status
        if node == "/DEV1234/SGCHANNELS/0/AWG/READY":
            return ready
        return RuntimeError("Undefined Node")

    awg_mock = mock_connection.return_value.awgModule.return_value
    awg_mock.getDouble.side_effect = get_side_effect
    awg_mock.getInt.side_effect = get_side_effect
    mock_connection.return_value.getInt.side_effect = get_side_effect

    # everything ok
    awg_module.load_sequencer_program("Hello")
    awg_mock.set.assert_any_call("/device", "DEV1234")
    awg_mock.set.assert_any_call("/index", 0)
    assert len(awg_mock.set.call_args_list) == 3
    awg_mock.set.assert_called_with("/compiler/sourcestring", "Hello")
    awg_mock.execute.assert_called()

    # Compiler timeout
    compiler_status = -1
    with pytest.raises(TimeoutError) as e_info:
        awg_module.load_sequencer_program("Hello", timeout=0.5)

    # Compiler error
    compiler_status = 1
    with pytest.raises(RuntimeError) as e_info:
        awg_module.load_sequencer_program("Hello")

    # Compiler warning
    compiler_status = 2
    awg_module.load_sequencer_program("Hello")
    assert "Warning during sequencer compilation" in caplog.messages[-1]
    compiler_status = 0

    # Upload timeout
    elf_status = 2
    ready = 0
    upload_process = cycle([0])
    with pytest.raises(TimeoutError) as e_info:
        awg_module.load_sequencer_program("Hello", timeout=0.5)

    # Upload error
    upload_process = cycle([1])
    elf_status = 1
    ready = 1
    with pytest.raises(RuntimeError) as e_info:
        awg_module.load_sequencer_program("Hello", timeout=0.5)

    # Empty string sequencer program
    with pytest.raises(ValueError):
        awg_module.load_sequencer_program("")
    with pytest.raises(ValueError):
        awg_module.load_sequencer_program(None)


def test_load_sequencer_program_qc(mock_connection, awg_module_qc):
    compiler_status = 0
    upload_process = iter([0, 0.2, 1, 1])
    ready = 1
    elf_status = 0

    def get_side_effect(node):
        if node == "/compiler/status":
            return compiler_status
        if node == "/progress":
            return next(upload_process)
        if node == "/elf/status":
            return elf_status
        if node == "/DEV1234/SGCHANNELS/0/AWG/READY":
            return ready
        return RuntimeError("Undefined Node")

    awg_mock = mock_connection.return_value.awgModule.return_value
    awg_mock.getDouble.side_effect = get_side_effect
    awg_mock.getInt.side_effect = get_side_effect
    mock_connection.return_value.getInt.side_effect = get_side_effect

    # everything ok
    awg_module_qc.load_sequencer_program("Hello")
    awg_mock.set.assert_any_call("/device", "DEV1234")
    awg_mock.set.assert_any_call("/index", 0)
    awg_mock.set.assert_any_call("/sequencertype", "sg")
    assert len(awg_mock.set.call_args_list) == 4
    awg_mock.set.assert_called_with("/compiler/sourcestring", "Hello")
    awg_mock.execute.assert_called()


def test_command_table(awg_module):
    assert isinstance(awg_module.commandtable, CommandTableNode)
    assert awg_module.commandtable.raw_tree == awg_module.raw_tree + ("commandtable",)


def test_write_to_waveform_memory(
    waveform_descriptors_json, mock_connection, awg_module
):
    mock_connection.return_value.get.return_value = OrderedDict(
        [
            (
                "/dev12044/sgchannels/0/awg/waveform/descriptors",
                [
                    {
                        "timestamp": 1158178198389432,
                        "flags": 0,
                        "vector": waveform_descriptors_json,
                    }
                ],
            )
        ]
    )
    waveforms = Waveforms()
    wave1 = 1.0 * np.ones(1008)
    wave2 = -1.0 * np.ones(1008)
    marker = np.zeros(1008)
    waveforms[0] = (wave1, wave2)
    waveforms[1] = (wave1, wave2, marker)
    awg_module.write_to_waveform_memory(waveforms)
    assert (
        mock_connection.return_value.set.call_args[0][0][0][0]
        == "/dev1234/sgchannels/0/awg/waveform/waves/0"
    )
    assert (
        mock_connection.return_value.set.call_args[0][0][1][0]
        == "/dev1234/sgchannels/0/awg/waveform/waves/1"
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][0][1]
        == waveforms.get_raw_vector(0)
    )
    assert all(
        mock_connection.return_value.set.call_args[0][0][1][1]
        == waveforms.get_raw_vector(1)
    )

    awg_module.write_to_waveform_memory(waveforms, [0])
    assert (
        mock_connection.return_value.set.call_args[0][0][0][0]
        == "/dev1234/sgchannels/0/awg/waveform/waves/0"
    )
    assert len(mock_connection.return_value.set.call_args[0][0]) == 1

    # to big index
    waveforms[10] = (wave1, wave2)
    with pytest.raises(IndexError) as e_info:
        awg_module.write_to_waveform_memory(waveforms)
    del waveforms[10]
    # assign to filler
    waveforms[2] = (wave1, wave2)
    with pytest.raises(RuntimeError) as e_info:
        awg_module.write_to_waveform_memory(waveforms)


def test_read_from_waveform_memory(
    waveform_descriptors_json, mock_connection, awg_module
):
    waveform_descriptiors = json.loads(waveform_descriptors_json)

    single_wave_result = []

    def get_side_effect(nodes, **kwargs):
        if nodes.lower() == "/dev1234/sgchannels/0/awg/waveform/descriptors":
            return OrderedDict(
                [
                    (
                        "/dev1234/sgchannels/0/awg/waveform/descriptors",
                        [
                            {
                                "timestamp": 1158178198389432,
                                "flags": 0,
                                "vector": json.dumps(waveform_descriptiors),
                            }
                        ],
                    )
                ]
            )
        if "/dev1234/sgchannels/0/awg/waveform/waves/" in nodes.lower():
            if nodes[-1] == "*":
                return OrderedDict(
                    [
                        (
                            "/dev1234/sgchannels/0/awg/waveform/waves/0",
                            [
                                {
                                    "timestamp": 338544371667920,
                                    "flags": 0,
                                    "vector": zi_utils.convert_awg_waveform(
                                        np.ones(1008), -np.ones(1008), np.ones(1008)
                                    ),
                                }
                            ],
                        ),
                        (
                            "/dev1234/sgchannels/0/awg/waveform/waves/1",
                            [
                                {
                                    "timestamp": 338544371667920,
                                    "flags": 0,
                                    "vector": [],
                                }
                            ],
                        ),
                        (
                            "/dev1234/sgchannels/0/awg/waveform/waves/2",
                            [
                                {
                                    "timestamp": 338544371667920,
                                    "flags": 0,
                                    "vector": [],
                                }
                            ],
                        ),
                    ]
                )
            else:
                return OrderedDict(
                    [
                        (
                            f"/dev1234/sgchannels/0/awg/waveform/waves/{nodes[-1]}",
                            [
                                {
                                    "timestamp": 338544371667920,
                                    "flags": 0,
                                    "vector": single_wave_result,
                                }
                            ],
                        )
                    ]
                )
        raise RuntimeError()

    mock_connection.return_value.get.side_effect = get_side_effect
    waveforms = awg_module.read_from_waveform_memory()
    assert all(waveforms[0][0] == np.ones(1008))
    assert all(waveforms[0][1] == -np.ones(1008))
    assert all(waveforms[0][2] == np.ones(1008))
    assert all(waveforms[1][0] == np.ones(0))
    assert all(waveforms[1][1] == np.ones(0))
    assert all(waveforms[1][2] == np.ones(0))

    # single Node Acces
    single_wave_result = zi_utils.convert_awg_waveform(
        np.ones(1008), -np.ones(1008), np.ones(1008)
    )
    waveforms = awg_module.read_from_waveform_memory([0])
    assert len(waveforms) == 1
    assert all(waveforms[0][0] == np.ones(1008))
    assert all(waveforms[0][1] == -np.ones(1008))
    assert all(waveforms[0][2] == np.ones(1008))

    single_wave_result = zi_utils.convert_awg_waveform(
        np.ones(1008), -np.ones(1008), None
    )
    waveform_descriptiors["waveforms"][1]["marker_bits"] = "0;0"
    waveforms = awg_module.read_from_waveform_memory([1])
    assert len(waveforms) == 1
    assert all(waveforms[1][0] == np.ones(1008))
    assert all(waveforms[1][1] == -np.ones(1008))
    assert waveforms[1][2] == None

    single_wave_result = zi_utils.convert_awg_waveform(
        np.ones(1008), None, np.ones(1008)
    )
    waveform_descriptiors["waveforms"][1]["channels"] = "1"
    waveform_descriptiors["waveforms"][1]["marker_bits"] = "1;0"
    waveforms = awg_module.read_from_waveform_memory([1])
    assert len(waveforms) == 1
    assert all(waveforms[1][0] == np.ones(1008))
    assert waveforms[1][1] == None
    assert all(waveforms[1][2] == np.ones(1008))

    single_wave_result = zi_utils.convert_awg_waveform(np.ones(1008), None, None)
    waveform_descriptiors["waveforms"][1]["channels"] = "1"
    waveform_descriptiors["waveforms"][1]["marker_bits"] = "0;0"
    waveforms = awg_module.read_from_waveform_memory([1])
    assert len(waveforms) == 1
    assert all(waveforms[1][0] == np.ones(1008))
    assert waveforms[1][1] == None
    assert waveforms[1][2] == None
