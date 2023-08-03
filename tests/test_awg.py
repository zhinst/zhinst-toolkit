import json
from collections import OrderedDict
from itertools import cycle

import numpy as np
import pytest
import zhinst.utils as zi_utils
from zhinst.core import compile_seqc

from zhinst.toolkit.driver.nodes.awg import CommandTableNode, Waveforms


@pytest.fixture()
def waveform_descriptors_json(data_dir):
    json_path = data_dir / "waveform_descriptors.json"
    with json_path.open("r", encoding="UTF-8") as file:
        return file.read()


def test_enable_sequencer(mock_connection, shfsg):
    shfsg.sgchannels[0].awg.enable_sequencer(single=True)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/sgchannels/0/awg/single", 1
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/sgchannels/0/awg/enable", 1
    )

    shfsg.sgchannels[0].awg.enable_sequencer(single=False)
    mock_connection.return_value.set.assert_called_with(
        "/dev1234/sgchannels/0/awg/single", 0
    )
    mock_connection.return_value.syncSetInt.assert_called_with(
        "/dev1234/sgchannels/0/awg/enable", 1
    )


def test_enable_sequencer_error(mock_connection, shfsg):
    mock_connection.return_value.syncSetInt.return_value = 0
    with pytest.raises(RuntimeError):
        shfsg.sgchannels[0].awg.enable_sequencer(single=True)

    with pytest.raises(RuntimeError):
        shfsg.sgchannels[0].awg.enable_sequencer(single=False)


def test_wait_done(mock_connection, shfsg):
    single = 0
    enable = iter([])

    def get_side_effect(node, **kwargs):
        if node.lower() == "/dev1234/sgchannels/0/awg/single":
            return {node: {"timestamp": [0], "value": [single]}}
        if node.lower() == "/dev1234/sgchannels/0/awg/enable":
            return {node: {"timestamp": [0], "value": [next(enable)]}}
        raise RuntimeError("Node not found")

    def get_int_side_effect(node):
        return get_side_effect(node)[node]["value"][0]

    mock_connection.return_value.get.side_effect = get_side_effect
    mock_connection.return_value.getInt.side_effect = get_int_side_effect

    # if not single mode this function throws a RuntimeError
    with pytest.raises(RuntimeError) as e_info:
        shfsg.sgchannels[0].awg.wait_done()

    # already finished
    single = 1
    enable = iter([0] * 2)
    shfsg.sgchannels[0].awg.wait_done()
    # finishes in time
    single = 1
    enable = iter([1] * 3 + [0] * 2)
    shfsg.sgchannels[0].awg.wait_done()
    # don't finish
    single = 1
    enable = cycle([1])
    with pytest.raises(TimeoutError) as e_info:
        shfsg.sgchannels[0].awg.wait_done(timeout=0.1)


def test_load_sequencer_program(mock_connection, shfsg):

    # everything ok
    elf, info_original = compile_seqc("setTrigger(1);", "SHFSG8", [], 0)
    info = shfsg.sgchannels[0].awg.load_sequencer_program("setTrigger(1);")
    mock_connection.return_value.set.assert_called_once()
    assert (
        mock_connection.return_value.set.call_args[0][0]
        == "/dev1234/sgchannels/0/awg/elf/data"
    )
    assert mock_connection.return_value.set.call_args[0][1] == elf
    assert info == info_original

    # Compiler error
    with pytest.raises(RuntimeError) as e_info:
        shfsg.sgchannels[0].awg.load_sequencer_program("Hello")

    # Empty string sequencer program
    with pytest.raises(RuntimeError):
        shfsg.sgchannels[0].awg.load_sequencer_program("")
    with pytest.raises(RuntimeError):
        shfsg.sgchannels[0].awg.load_sequencer_program(None)

    # Upload error
    mock_connection.return_value.set.side_effect = RuntimeError()
    mock_connection.return_value.setVector.side_effect = RuntimeError()
    with pytest.raises(RuntimeError):
        shfsg.sgchannels[0].awg.load_sequencer_program("setTrigger(1);")


def test_load_sequencer_program_qc(mock_connection, shfqc):
    elf, info_original = compile_seqc("setTrigger(1);", "SHFQC", [], 0, sequencer="sg")
    info = shfqc.sgchannels[0].awg.load_sequencer_program("setTrigger(1);")
    mock_connection.return_value.set.assert_called_once()
    assert (
        mock_connection.return_value.set.call_args[0][0]
        == "/dev1234/sgchannels/0/awg/elf/data"
    )
    assert mock_connection.return_value.set.call_args[0][1] == elf
    assert info == info_original


def test_command_table(shfsg):
    assert isinstance(shfsg.sgchannels[0].awg.commandtable, CommandTableNode)
    assert shfsg.sgchannels[0].awg.commandtable.raw_tree == shfsg.sgchannels[
        0
    ].awg.raw_tree + ("commandtable",)


def test_write_to_waveform_memory(waveform_descriptors_json, mock_connection, shfsg):
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
    shfsg.sgchannels[0].awg.write_to_waveform_memory(waveforms)
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

    shfsg.sgchannels[0].awg.write_to_waveform_memory(waveforms, [0])
    assert (
        mock_connection.return_value.set.call_args[0][0][0][0]
        == "/dev1234/sgchannels/0/awg/waveform/waves/0"
    )
    assert len(mock_connection.return_value.set.call_args[0][0]) == 1

    # existing transaction
    with shfsg.sgchannels[0].awg.root.set_transaction():
        shfsg.sgchannels[0].awg.dio.highbits(0)
        shfsg.sgchannels[0].awg.write_to_waveform_memory(waveforms)

    mock_connection.return_value.set.call_args[0][0][0][
        0
    ] == "/dev1234/sgchannels/0/awg/dio/highbits"
    assert len(mock_connection.return_value.set.call_args[0][0]) == 3


def test_read_from_waveform_memory(waveform_descriptors_json, mock_connection, shfsg):
    waveform_descriptiors = json.loads(waveform_descriptors_json)

    single_wave_result = []

    def get_side_effect(nodes, **kwargs):
        if "/dev1234/sgchannels/0/awg/waveform/descriptors" in nodes.lower():
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
                    ),
                ]
            )
        if "/dev1234/sgchannels/0/awg/waveform/waves/" in nodes.lower():
            return_value = []
            if "waves/0" in nodes:
                return_value.append(
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
                    )
                )
            if "waves/1" in nodes:
                return_value.append(
                    (
                        "/dev1234/sgchannels/0/awg/waveform/waves/1",
                        [
                            {
                                "timestamp": 338544371667920,
                                "flags": 0,
                                "vector": single_wave_result,
                            }
                        ],
                    )
                )
            if "waves/2" in nodes:
                return_value.append(
                    (
                        "/dev1234/sgchannels/0/awg/waveform/waves/2",
                        [
                            {
                                "timestamp": 338544371667920,
                                "flags": 0,
                                "vector": single_wave_result,
                            }
                        ],
                    )
                )
            if "waves/2" in nodes:
                return_value.append(
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
                )
            return OrderedDict(return_value)
        raise RuntimeError()

    mock_connection.return_value.get.side_effect = get_side_effect
    waveforms = shfsg.sgchannels[0].awg.read_from_waveform_memory()
    mock_connection.return_value.get.assert_called_with(
        "/dev1234/sgchannels/0/awg/waveform/waves/0,/dev1234/sgchannels/0/awg/waveform/waves/1,/dev1234/sgchannels/0/awg/waveform/waves/3",
        settingsonly=False,
        flat=True,
    )
    assert all(waveforms[0][0] == np.ones(1008))
    assert all(waveforms[0][1] == -np.ones(1008))
    assert all(waveforms[0][2] == np.ones(1008))
    assert all(waveforms[1][0] == np.ones(0))
    assert all(waveforms[1][1] == np.ones(0))
    assert all(waveforms[1][2] == np.ones(0))

    # single Node Access
    single_wave_result = zi_utils.convert_awg_waveform(
        np.ones(1008), -np.ones(1008), np.ones(1008)
    )
    waveforms = shfsg.sgchannels[0].awg.read_from_waveform_memory([0])
    mock_connection.return_value.get.assert_called_with(
        "/dev1234/sgchannels/0/awg/waveform/waves/0",
        settingsonly=False,
        flat=True,
    )
    assert len(waveforms) == 1
    assert all(waveforms[0][0] == np.ones(1008))
    assert all(waveforms[0][1] == -np.ones(1008))
    assert all(waveforms[0][2] == np.ones(1008))

    single_wave_result = zi_utils.convert_awg_waveform(
        np.ones(1008), -np.ones(1008), None
    )
    waveform_descriptiors["waveforms"][1]["marker_bits"] = "0;0"
    waveforms = shfsg.sgchannels[0].awg.read_from_waveform_memory([1])
    assert len(waveforms) == 1
    assert all(waveforms[1][0] == np.ones(1008))
    assert all(waveforms[1][1] == -np.ones(1008))
    assert waveforms[1][2] is None

    single_wave_result = zi_utils.convert_awg_waveform(
        np.ones(1008), None, np.ones(1008)
    )
    waveform_descriptiors["waveforms"][1]["channels"] = "1"
    waveform_descriptiors["waveforms"][1]["marker_bits"] = "1;0"
    waveforms = shfsg.sgchannels[0].awg.read_from_waveform_memory([1])
    assert len(waveforms) == 1
    assert all(waveforms[1][0] == np.ones(1008))
    assert waveforms[1][1] is None
    assert all(waveforms[1][2] == np.ones(1008))

    single_wave_result = zi_utils.convert_awg_waveform(np.ones(1008), None, None)
    waveform_descriptiors["waveforms"][1]["channels"] = "1"
    waveform_descriptiors["waveforms"][1]["marker_bits"] = "0;0"
    waveforms = shfsg.sgchannels[0].awg.read_from_waveform_memory([1])
    assert len(waveforms) == 1
    assert all(waveforms[1][0] == np.ones(1008))
    assert waveforms[1][1] is None
    assert waveforms[1][2] is None


def test_read_from_waveform_memory_large_index(data_dir, mock_connection, shfsg):
    json_path = data_dir / "waveform_descriptors_large.json"
    with json_path.open("r", encoding="UTF-8") as file:
        waveform_descriptiors = json.loads(file.read())

    def get_side_effect(nodes, **kwargs):
        if "/dev1234/sgchannels/0/awg/waveform/descriptors" in nodes.lower():
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
                    ),
                ]
            )
        if "/dev1234/sgchannels/0/awg/waveform/waves/" in nodes.lower():
            return OrderedDict(
                [
                    (
                        "/dev1234/sgchannels/0/awg/waveform/waves/11",
                        [
                            {
                                "timestamp": 338544371667920,
                                "flags": 0,
                                "vector": zi_utils.convert_awg_waveform(
                                    np.ones(1008), -np.ones(1008), np.ones(1008)
                                ),
                            }
                        ],
                    )
                ]
            )
        raise RuntimeError()

    mock_connection.return_value.get.side_effect = get_side_effect
    waveforms = shfsg.sgchannels[0].awg.read_from_waveform_memory()
    mock_connection.return_value.get.assert_called_with(
        "/dev1234/sgchannels/0/awg/waveform/waves/11",
        settingsonly=False,
        flat=True,
    )
    assert all(waveforms[11][0] == np.ones(1008))
    assert all(waveforms[11][1] == -np.ones(1008))
    assert all(waveforms[11][2] == np.ones(1008))
