import json
from array import array
from collections import OrderedDict
from pathlib import Path
from types import GeneratorType
from unittest.mock import MagicMock, Mock
from copy import deepcopy
import pickle
import gc
from itertools import cycle

import pytest
import numpy as np

from zhinst.toolkit.driver.devices import HDAWG
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.connection_dict import ConnectionDict
from zhinst.toolkit.nodetree.node import NodeList
from zhinst.toolkit.nodetree.helper import (
    resolve_wildcards_labone,
    not_callable_in_transactions,
)
from zhinst.toolkit.exceptions import ToolkitError

from zhinst.core.errors import CoreError


@pytest.fixture()
def data_dir(request):
    yield Path(request.fspath).parent / "data"


@pytest.fixture()
def connection(data_dir):
    json_path = data_dir / "nodedoc_dev1234_zi.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()

    connection = MagicMock()
    connection.listNodesJSON.return_value = nodes_json
    yield connection


def test_init(connection, data_dir):
    tree = NodeTree(connection)
    connection.listNodesJSON.assert_called_once_with("*")
    assert "zi" in tree
    assert "ZI" in tree
    assert "dev1234" in tree
    assert "DEV1234" in tree
    assert "zi" in dir(tree)
    assert "dev1234" in dir(tree)

    tree = NodeTree(connection, "DEV1234")
    connection.listNodesJSON.assert_called_with("*")
    assert "zi" in tree
    assert "ZI" in tree
    assert "dev1234" not in tree
    assert "DEV1234" not in tree
    assert "zi" in dir(tree)
    assert "dev1234" not in dir(tree)

    json_path = data_dir / "nodedoc_daq_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    connection_module = MagicMock()
    connection_module.listNodesJSON.return_value = nodes_json
    tree = NodeTree(connection_module)
    connection_module.listNodesJSON.assert_called_with("*")
    assert "awgcontrol" in tree

    connection_broken = MagicMock()
    connection_broken.listNodesJSON.return_value = '{\n"zi/open": {\n"Node": "/ZI/OPEN"\n},\n"zi/close": {\n"Node": "/ZI/CLOSE"\n}\n}\n'
    with pytest.raises(Exception) as e_info:
        NodeTree(connection_broken)
    assert "Leading slash not found" in e_info.value.args[0]


def test_init_preloaded_json(nodedoc_dev1234_json):
    nodes_json = json.loads(nodedoc_dev1234_json)
    connection = MagicMock()  # plain mock without json info
    tree = NodeTree(connection, prefix_hide="DEV1234", preloaded_json=nodes_json)
    assert tree.prefix_hide == "dev1234"
    connection.listNodesJSON.mock_object.assert_not_called()


def test_to_raw_path(connection):
    tree = NodeTree(connection)

    with pytest.raises(ValueError):
        tree.to_raw_path("hello/world")

    assert tree.to_raw_path(Node(tree, tuple())) == "/"

    tree = NodeTree(connection, "DEV1234")
    assert tree.to_raw_path(Node(tree, tuple())) == "/dev1234"


def test_to_raw_path_capital(connection):
    tree = NodeTree(connection)
    assert tree.to_raw_path("/dev1234/demods/0/enable") == "/dev1234/demods/0/enable"
    assert tree.to_raw_path("/DEV1234/demods/0/enable") == "/dev1234/demods/0/enable"
    assert tree.to_raw_path("/dev1234/Demods/0/Enable") == "/dev1234/demods/0/enable"


def test_root_node(connection):
    tree = NodeTree(connection, "DEV1234")

    root_node = Node(tree, tuple())
    assert "demods" in root_node


def test_node_contains(connection):
    tree = NodeTree(connection, "DEV1234")

    assert "rate" in tree.demods[0]  # existing child node
    assert "invalid" not in tree.demods[0]  # non existing child node
    assert "node" not in tree.demods[0]  # property


def test_node_iter(connection):
    tree = NodeTree(connection, "DEV1234")

    childs = []
    for child, info in tree.demods[0]:
        childs.append(child)
        assert child.node_info.path.lower() == info["Node"].lower()

    assert all([child.raw_tree[-1] in tree.demods[0] for child in childs])

    childs = []
    for child, info in tree.demods["*"]:
        childs.append(child)
        assert child.node_info.path.lower() == info["Node"].lower()
    assert all([child.raw_tree[-1] in tree.demods["*"] for child in childs])


def test_node_access(connection):
    tree = NodeTree(connection, "DEV1234")

    assert tree.demods.root == tree

    # test local variable
    assert not tree._test
    assert not tree.demods._test
    # test attribute vs item
    assert tree.demods == tree["demods"]
    assert tree.demods == tree["/demods"]
    assert tree.demods.test == tree["demods/test"]
    assert tree.demods.test == tree.demods["/test"]
    assert tree.demods.test.world == tree.demods["test/world"]

    # buildin keywords are escaped with tailing underscore
    assert tree.in_.test == tree["in/test"]
    assert tree.test.and_ == tree["test/and"]

    # test invalid nodes
    assert tree.no.real.element.raw_tree == ("no", "real", "element")
    assert str(tree.no.real.element) == "/dev1234/no/real/element"
    with pytest.raises(KeyError) as e_info:
        tree.no.real.element()
    assert e_info.value.args[0] == str(tree.no.real.element)


def test_node_access_capital(connection):
    tree = NodeTree(connection, "DEV1234")
    assert tree.demods[0].enable != tree.Demods[0].Enable
    assert tree.demods[0].enable == tree["Demods/0/Enable"]


def test_node(connection):
    tree = NodeTree(connection, "DEV1234")
    # test properties of node
    assert (
        repr(tree.demods[0].rate.node_info)
        == 'NodeInfo("/dev1234/demods/0/rate",leaf-node)'
    )
    assert (
        str(tree.demods[0].rate.node_info)
        == """\
/dev1234/demods/0/rate
Defines the demodulator sampling rate, the number of samples that are sent to the host \
computer per second. A rate of about 7-10 higher as compared to the filter bandwidth \
usually provides sufficient aliasing suppression. This is also the rate of data \
received by LabOne Data Server and saved to the computer hard disk. This setting has \
no impact on the sample rate on the auxiliary outputs connectors. Note: the value \
inserted by the user may be approximated to the nearest value supported by the \
instrument.
Properties: Read, Write, Setting
Type: Double
Unit: 1/s"""
    )

    assert "Options" in str(tree.demods[0].enable.node_info)
    assert "Partial node" in str(tree.demods[0].node_info)
    assert "Contains wildcards" in str(tree.demods["*"].node_info)

    assert "description" in dir(tree.demods[0].rate.node_info)

    assert tree.demods[0].rate.node_info.path
    assert tree.demods[0].rate.node_info.description
    assert tree.demods[0].rate.node_info.type
    assert tree.demods[0].rate.node_info.unit
    assert tree.demods[0].trigger.node_info.options.get(1)
    assert tree.demods[0].trigger.node_info.is_setting
    assert not tree.demods[0].trigger.node_info.is_vector
    assert not tree.system.impedance.calib.user.data.node_info.is_setting
    assert tree.system.impedance.calib.user.data.node_info.is_vector
    assert tree.system.node_info.is_setting is None
    assert tree.system.node_info.is_vector is None

    # dir of nested node
    assert "0" in dir(tree.demods)
    assert "rate" in dir(tree.demods[0])

    # contains
    assert "Description" in tree.demods[0].rate.node_info
    assert "Test" not in tree.demods[0].rate.node_info

    # parsers
    def add_one(value):
        return value + 1

    def sub_one(value):
        return value - 1

    tree.update_node(
        "/DEV1234/test/path/0",
        {
            "SetParser": add_one,
            "GetParser": sub_one,
        },
        add=True,
    )
    assert tree.test.path[0].node_info.get_parser(5) == 4
    assert tree.test.path[0].node_info.set_parser(5) == 6

    tree.update_node(
        "/DEV1234/test/path/0",
        {"SetParser": [add_one, add_one], "GetParser": [sub_one, sub_one]},
        add=True,
    )
    assert tree.test.path[0].node_info.get_parser(5) == 3
    assert tree.test.path[0].node_info.set_parser(5) == 7

    # dynamic node
    with pytest.raises(KeyError):
        tree.demods.waves[0].node_info.unit


def test_send_set_list(connection):
    tree = NodeTree(connection, "DEV1234")
    node = tree.demods[0]
    settings = [(str(node.freq), 2000)]

    node._send_set_list(settings)

    connection.set.assert_called_once_with(settings)


def test_send_set_list_transaction(connection):
    tree = NodeTree(connection, "DEV1234")
    node = tree.demods[0]
    settings = [(str(node.freq), 2000)]

    with tree.set_transaction():
        node.enable(True)
        node._send_set_list(settings)

        connection.set.assert_not_called()

    connection.set.assert_called_once_with([(str(node.enable), True)] + settings)


def test_add_raw_list_outside_transaction(connection):
    tree = NodeTree(connection, "DEV1234")
    transaction = tree.transaction
    settings = [("/dev1234/test1", True), ("/dev1234/test2", 17)]

    with pytest.raises(ToolkitError, match="No set transaction is in progress."):
        transaction.add_raw_list(settings)


def test_add_raw_list(connection):
    tree = NodeTree(connection, "DEV1234")
    transaction = tree.transaction
    settings = [("/dev1234/test1", True), ("/dev1234/test2", 17)]

    with tree.set_transaction():
        transaction.add("/dev1234/test3", 3.5)
        transaction.add_raw_list(settings)
        transaction.add("/dev1234/test4", False)

    connection.set.assert_called_once_with(
        [
            ("/dev1234/test3", 3.5),
            ("/dev1234/test1", True),
            ("/dev1234/test2", 17),
            ("/dev1234/test4", False),
        ]
    )


def test_not_callable_in_transactions(connection):
    tree = NodeTree(connection, "DEV1234")
    node = tree.demods[0]

    @not_callable_in_transactions
    def example_func(node: Node, kwarg=None):
        return True

    example_func(node)  # no error

    with pytest.raises(
        RuntimeError, match="'example_func' cannot be called inside a transaction"
    ):
        with tree.set_transaction():
            example_func(node)


def test_node_dir_property_not_duplicated(connection):
    class MockNode(Node):
        def __init__(self, root: "NodeTree", tree: tuple):
            self._root = root
            self._tree = tree

        @property
        def features(self):
            pass

    tree = NodeTree(connection, "DEV1234")
    assert "features" in dir(tree)
    node = MockNode(tree, ())
    assert len(dir(node)) == len(set(dir(node)))


def test_wildcard_node(connection):
    tree = NodeTree(connection, "DEV1234")
    wildcard_node = tree.demods["*"].rate
    assert wildcard_node.node_info.path == "/dev1234/demods/*/rate"
    with pytest.raises(KeyError) as e_info:
        wildcard_node.node_info.description

    # TODO add dummy Data to mock
    wildcard_node()
    wildcard_node(1)
    with tree.set_transaction():
        tree.demods["*"].rate(1)

    connection.get.return_value = None
    with pytest.raises(KeyError) as e_info:
        tree.hello["*"].rate()
    connection.set.side_effect = RuntimeError("test")
    with pytest.raises(KeyError) as e_info:
        tree.hello["*"].rate(1)


def test_get_cached(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.demods[0].adcselect()
    connection.getInt.assert_called_with(tree.demods[0].adcselect.node_info.path)
    tree.demods[0].rate()
    connection.getDouble.assert_called_with(tree.demods[0].rate.node_info.path)
    tree.features.serial()
    connection.getString.assert_called_with(tree.features.serial.node_info.path)

    # Complex Double
    tree.update_node("demods/0/rate", {"Type": "Complex Double"})
    tree.demods[0].rate()
    connection.getComplex.assert_called_with(tree.demods[0].rate.node_info.path)
    connection.getComplex = None
    with pytest.raises(TypeError) as e_info:
        tree.demods[0].rate()

    # ZIVectorData
    with pytest.raises(TypeError) as e_info:
        tree.system.impedance.calib.user.data()

    # ZIDemodSample
    tree.demods[0].sample()
    connection.getSample.assert_called_with(tree.demods[0].sample.node_info.path)
    connection.getSample = None
    with pytest.raises(TypeError) as e_info:
        tree.demods[0].sample()

    # ZIDIOSample
    tree.dios[0].input()
    connection.getDIO.assert_called_with(tree.dios[0].input.node_info.path)

    # ZIAdvisorWave
    tree.update_node(tree.dios[0].input, {"Type": "ZIAdvisorWave"})
    with pytest.raises(StopIteration):
        tree.dios[0].input()
    connection.get.assert_called_with(tree.dios[0].input.node_info.path, flat=True)

    # invalid type
    tree.update_node(tree.dios[0].input, {"Type": "InvalidType"})
    with pytest.raises(RuntimeError):
        tree.dios[0].input()


def test_get_deep(connection):
    tree = NodeTree(connection, "DEV1234")

    with pytest.raises(TypeError) as e_info:
        tree.demods[0].rate(deep=True)
        connection.get.assert_called_with(
            tree.demods[0].rate.node_info.path, settingsonly=False, flat=True
        )
    with pytest.raises(TypeError) as e_info:
        tree.demods[0].rate(deep=True, test=True)

    # overwrite internally used kwarg
    with pytest.raises(TypeError) as e_info:
        tree.demods[0].rate(deep=True, settingsonly=True)

    connection.get.return_value = OrderedDict()
    with pytest.raises(TypeError) as e_info:
        tree.demods[0].rate(deep=True)

    # Real data
    # double node
    connection.get.return_value = OrderedDict(
        [
            (
                "/dev1234/demods/0/rate",
                {
                    "timestamp": array("q", [1236389131550]),
                    "value": array("d", [1674.10717773]),
                },
            )
        ]
    )
    timestamp, data = tree.demods[0].rate(deep=True)
    assert timestamp == 1236389131550
    assert data == 1674.10717773
    # vector node
    connection.get.return_value = OrderedDict(
        [
            (
                "/dev1234/system/impedance/calib/user/data",
                [
                    {
                        "timestamp": 3880906635,
                        "flags": 0,
                        "vector": array("l", [123, 10, 32, 10, 125, 10]),
                    }
                ],
            )
        ]
    )
    timestamp, data = tree.demods[0].sample(deep=True)
    assert timestamp == 3880906635
    assert data == array("l", [123, 10, 32, 10, 125, 10])
    # HF2 node
    connection.get.return_value = OrderedDict(
        [("/dev1234/demods/0/rate", np.array([1674.10717773]))]
    )
    timestamp, data = tree.demods[0].sample(deep=True)
    assert data == 1674.10717773
    assert timestamp is None


def test_get_deep_module(connection):
    tree = NodeTree(connection, "DEV1234")
    data = OrderedDict(
        [
            (
                "/dev1234/demods/0/rate",
                {
                    "timestamp": array("q", [1236389131550]),
                    "value": array("d", [1674.10717773]),
                },
            )
        ]
    )
    connection.get.side_effect = [TypeError(), data]
    tree.demods[0].rate(deep=True)
    connection.get.assert_called_with(tree.demods[0].rate.node_info.path, flat=True)


def test_get_wildcard(connection):
    tree = NodeTree(connection, "DEV1234")

    connection.get.return_value = OrderedDict(
        [
            (
                "/dev1234/demods/0/impedance",
                {
                    "timestamp": array("q", [3880906635]),
                    "value": array("l", [123]),
                },
            )
        ]
    )
    result = tree.demods()
    assert result[tree.demods[0].impedance] == 123
    connection.get.assert_called_with("/dev1234/demods", settingsonly=False, flat=True)

    # deep includes the timestamp
    result = tree.demods(deep=True)
    assert result[tree.demods[0].impedance] == (3880906635, 123)

    # nested dict
    result = tree.demods(flat=False)
    assert isinstance(result, OrderedDict)

    # nested dict
    result = tree.demods["*"].impedance(flat=False)
    assert isinstance(result, OrderedDict)

    # invalid node
    with pytest.raises(KeyError) as e_info:
        tree.invalid()

    # HF2 support
    connection.get.return_value = OrderedDict(
        [("/dev1234/demods/0/impedance", np.array([125]))]
    )
    result = tree.demods()
    assert result[tree.demods[0].impedance] == 125
    connection.get.assert_called_with("/dev1234/demods", settingsonly=False, flat=True)

    result = tree.demods(deep=True)
    assert result[tree.demods[0].impedance] == (None, 125)

    connection.get.return_value = OrderedDict(
        [
            (
                "/dev1234/demods/0/impedance",
                {
                    "timestamp": array("q", [3880906635]),
                    "x": array("l", [123]),
                    "y": array("l", [123]),
                },
            )
        ]
    )
    result = tree.demods()
    assert (
        result[tree.demods[0].impedance]
        == connection.get.return_value["/dev1234/demods/0/impedance"]
    )
    connection.get.assert_called_with("/dev1234/demods", settingsonly=False, flat=True)


def test_module_get_wildcard(connection):
    tree = NodeTree(connection, "DEV1234")

    return_value = OrderedDict(
        [
            (
                "/dev1234/demods/0/impedance",
                {
                    "timestamp": array("q", [3880906635]),
                    "value": array("l", [123]),
                },
            )
        ]
    )
    connection.get.side_effect = [TypeError(), return_value]
    assert tree.demods()[tree.demods[0].impedance] == 123


def test_set(connection):
    tree = NodeTree(connection, "DEV1234")
    tree.demods[0].rate(22.0)
    connection.set.assert_called_with(tree.demods[0].rate.node_info.path, 22.0)
    tree.demods[0].rate(22.0, test=True)
    connection.set.assert_called_with(
        tree.demods[0].rate.node_info.path, 22.0, test=True
    )

    # sync set of nodes is only dependend on the input parameter not the
    # type of the node iself
    tree.demods[0].rate(22.0, deep=True)
    connection.syncSetDouble.assert_called_with(
        tree.demods[0].rate.node_info.path, 22.0
    )
    tree.demods[0].rate(0, deep=True)
    connection.syncSetInt.assert_called_once_with(tree.demods[0].rate.node_info.path, 0)
    tree.demods[0].rate("test", deep=True)
    connection.syncSetString.assert_called_once_with(
        tree.demods[0].rate.node_info.path, "test"
    )
    with pytest.raises(Exception) as e_info:
        tree.demods[0].rate(complex(2, -3), deep=True)

    connection.syncSetString = None
    with pytest.raises(TypeError):
        tree.demods[0].rate("test", deep=True)

    with pytest.raises(KeyError):
        tree.demods.test("test")


def test_set_partial(connection):
    tree = NodeTree(connection, "DEV1234")
    tree.demods[0](22.0)
    connection.set.assert_called_with(tree.demods[0]["*"].node_info.path, 22.0)


def test_runtimerror_set_set_vector(connection):
    # tree.system.impedance.calib.user.data does work with set, but for
    # testing purposes call it
    tree = NodeTree(connection, "DEV1234")
    connection.set = Mock(side_effect=RuntimeError)
    tree.system.impedance.calib.user.data(b"Test Binary Data")
    connection.setVector.assert_called_with(
        tree.system.impedance.calib.user.data.node_info.path, b"Test Binary Data"
    )


def test_runtimerror_set(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.demods[0].rate(22.0)
    connection.set.assert_called_with(tree.demods[0].rate.node_info.path, 22.0)

    connection.set = Mock(side_effect=RuntimeError)
    with pytest.raises(RuntimeError):
        tree.demods[0].rate(22.0)


def test_transactional_set(connection):
    tree = NodeTree(connection, "DEV1234")
    with tree.set_transaction():
        tree.demods[0].rate(22.0)
    connection.set.assert_called_once_with([("/dev1234/demods/0/rate", 22.0)])
    with tree.set_transaction():
        tree.demods[0].rate(22.0)
        tree.demods[0].phaseshift(1)
    connection.set.assert_called_with(
        [("/dev1234/demods/0/rate", 22.0), ("/dev1234/demods/0/phaseshift", 1)]
    )
    with tree.set_transaction():
        tree.demods[0].rate(22.0)
        tree.transaction.add("demods/0/phaseshift", 2)
    connection.set.assert_called_with(
        [("/dev1234/demods/0/rate", 22.0), ("/dev1234/demods/0/phaseshift", 2)]
    )

    with tree.set_transaction():
        tree.system.impedance.calib.user.data(b"Test Binary Data")
    connection.set.assert_called_with(
        [("/dev1234/system/impedance/calib/user/data", b"Test Binary Data")]
    )

    with pytest.raises(AttributeError) as e_info:
        tree.transaction.add("demods/0/phaseshift", 2)

    with pytest.raises(RuntimeError) as e_info:
        with tree.set_transaction():
            with tree.set_transaction():
                pass


def test_get_node_info_raw(connection):
    tree = NodeTree(connection, "DEV1234")
    # raw get
    assert tree.get_node_info_raw("demods/0/rate") == tree.get_node_info_raw(
        tree.demods[0].rate
    )
    assert tree.get_node_info_raw("/dev1234/demods/0/rate") == tree.get_node_info_raw(
        tree.demods[0].rate
    )
    with pytest.raises(KeyError) as e_info:
        tree.get_node_info_raw("zi/config/open")
    assert tree.get_node_info_raw("/zi/config/open") == tree.get_node_info_raw(
        tree.zi.config.open
    )
    with pytest.raises(KeyError) as e_info:
        tree.get_node_info_raw("/demods/0/rate")
    assert e_info.value.args[0] == "/demods/0/rate"
    with pytest.raises(KeyError):
        tree.get_node_info_raw("dev1234/demods/0/rate")
    with pytest.raises(KeyError) as e_info:
        tree.get_node_info_raw("no/real/element")
    assert e_info.value.args[0] == "/dev1234/no/real/element"

    # raw get wildcards
    assert tree.get_node_info_raw("demods/*/rate") == tree.get_node_info_raw(
        "demods/?/rate"
    )
    assert len(tree.get_node_info_raw("demods/0/*")) > 1
    with pytest.raises(KeyError) as e_info:
        tree.get_node_info_raw("demods/0/real/*")
    assert e_info.value.args[0] == "/dev1234/demods/0/real/*"
    with pytest.raises(KeyError) as e_info:
        tree.get_node_info_raw("demod/0/*")
    assert e_info.value.args[0] == "/dev1234/demod/0/*"


def test_update_node(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.update_node("demods/0/rate", {"Unit": "test"})
    assert tree.demods[0].rate.node_info.unit == "test"
    tree.update_node("demods/0/rate", {"Test": "test"})
    assert (
        next(iter(tree.get_node_info_raw("demods/0/rate").values())).get("Test", None)
        == "test"
    )
    tree.update_node("demods/0/rate", {"Unit": "test2", "Test2": True})
    assert tree.demods[0].rate.node_info.unit == "test2"
    assert next(iter(tree.get_node_info_raw("demods/0/rate").values())).get(
        "Test2", None
    )

    # new Node
    with pytest.raises(KeyError) as e_info:
        tree.update_node("/test", {"Node": "test"})
    assert e_info.value.args[0] == "/test"

    assert str(tree.test) == "/dev1234/test"
    tree.update_node("/test", {"Node": "test"}, add=True)
    tree.get_node_info_raw(tree.test)
    assert tree.test.node_info["Node"] == "test"

    assert str(tree.demods[0].test) == "/dev1234/demods/0/test"
    tree.update_node("demods/0/test", {"Node": "test"}, add=True)
    assert str(tree.demods[0].test) == "test"

    tree.update_node("demods/0/rate", {"Properties": "Write"})
    with pytest.raises(Exception) as e_info:
        tree.demods[0].rate()
    tree.update_node("demods/0/rate", {"Properties": "Read"})
    with pytest.raises(Exception) as e_info:
        tree.demods[0].rate(12)

    with pytest.raises(RuntimeError) as e_info:
        tree.update_node("hello/*/world", {}, add=True)


def test_update_nodes(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.update_nodes(
        {"demods/0/rate": {"Unit": "test"}, "demods/0/order": {"Unit": "test2"}}
    )
    assert tree.demods[0].rate.node_info.unit == "test"
    assert tree.demods[0].order.node_info.unit == "test2"

    with pytest.raises(KeyError) as e_info:
        tree.update_nodes(
            {"demods/0/rate": {"Unit": "test3"}, "test": {"Node": "test"}}
        )
    assert tree.demods[0].rate.node_info.unit == "test3"
    tree.update_nodes(
        {"demods/0/rate": {"Unit": "test3"}, "test": {"Node": "test4"}}, add=True
    )
    assert tree.test.node_info.path == "test4"
    assert tree.test.is_valid() is True

    tree.update_nodes(
        {"312/123": {"Unit": "test5"}, "testNOtexists": {"Node": "test5"}},
        add=False,
        raise_for_invalid_node=False,
    )
    assert tree.testNOtexists.is_valid() is False


def test_options(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.demods[0].trigger("continuous")
    connection.set.assert_called_with(
        tree.demods[0].trigger.node_info.path, "continuous"
    )

    tree.demods[0].trigger("continuou")
    connection.set.assert_called_with(
        tree.demods[0].trigger.node_info.path, "continuou"
    )

    connection.getInt.return_value = 0
    assert tree.demods[0].trigger() == tree.demods[0].trigger.node_info.enum.continuous

    connection.getInt.return_value = 12345678
    assert tree.demods[0].trigger() == 12345678


def test_nameless_options(connection):
    tree = NodeTree(connection, "DEV1234")

    options = tree.demods[0].order.node_info.options
    assert len(options) == 8
    assert options[1].enum == ""
    assert options[1].description == "1st order filter 6 dB/oct"

    assert tree.demods[0].order.node_info.enum is None


def test_multiple_options(connection):
    tree = NodeTree(connection, "DEV1234")

    options = tree.demods[0].adcselect.node_info.options

    assert options[0].enum == "sigin0"
    assert options[0].description == "Sig In 1"

    assert tree.demods[0].adcselect.node_info.enum.sigin0 == 0
    assert tree.demods[0].adcselect.node_info.enum.signal_input0 == 0

    assert tree.demods[0].adcselect.node_info.enum.currin0 == 1
    assert tree.demods[0].adcselect.node_info.enum.current_input0 == 1


def test_parser(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.update_node(
        "demods/0/rate",
        {
            "GetParser": lambda value: value + 10,
            "SetParser": lambda value: value + 10,
        },
    )
    connection.getDouble.return_value = 0
    assert tree.demods[0].rate() == 10
    tree.demods[0].rate(0)
    connection.set.assert_called_with(tree.demods[0].rate.node_info.path, 10)


def test_get_as_event(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.demods[0].sample.get_as_event()
    connection.getAsEvent.assert_called_once_with(tree.demods[0].sample.node_info.path)

    connection.getAsEvent.side_effect = RuntimeError()
    with pytest.raises(KeyError):
        tree.demods["*"].test.get_as_event()


def test_child_nodes(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.demods[0].child_nodes()
    connection.listNodes.assert_not_called()
    generator = tree.demods[0].child_nodes()
    assert isinstance(generator, GeneratorType)
    connection.listNodes.assert_not_called()
    list(generator)
    connection.listNodes.assert_called_once_with(
        tree.demods[0].node_info.path,
        recursive=False,
        leavesonly=False,
        settingsonly=False,
        streamingonly=False,
        subscribedonly=False,
        basechannelonly=False,
        excludestreaming=False,
        excludevectors=False,
    )
    list(
        tree.demods[0].sample.child_nodes(
            recursive=True,
            leavesonly=False,
            settingsonly=True,
            streamingonly=False,
            subscribedonly=True,
            basechannelonly=False,
            excludestreaming=True,
            excludevectors=False,
        )
    )
    connection.listNodes.assert_called_with(
        tree.demods[0].sample.node_info.path,
        recursive=True,
        leavesonly=False,
        settingsonly=True,
        streamingonly=False,
        subscribedonly=True,
        basechannelonly=False,
        excludestreaming=True,
        excludevectors=False,
    )
    connection.listNodes.return_value = [
        tree.demods[0].sample.node_info.path,
        tree.demods[0].rate.node_info.path,
    ]
    result = list(
        tree.demods[0].child_nodes(
            recursive=True,
            leavesonly=True,
            settingsonly=True,
            streamingonly=True,
            subscribedonly=True,
            basechannelonly=True,
            excludestreaming=True,
            excludevectors=True,
        )
    )
    connection.listNodes.assert_called_with(
        tree.demods[0].node_info.path,
        recursive=True,
        leavesonly=True,
        settingsonly=True,
        streamingonly=True,
        subscribedonly=True,
        basechannelonly=True,
        excludestreaming=True,
        excludevectors=True,
    )
    assert result == [tree.demods[0].sample, tree.demods[0].rate]

    # wildcard nodes
    connection.listNodes.side_effect = RuntimeError("Weird fail")
    with pytest.raises(RuntimeError) as e_info:
        list(tree.demods["*"].child_nodes())
    assert e_info.value.args[0] == "Weird fail"
    connection.listNodes.side_effect = CoreError("Unrelated Error", 1111)
    with pytest.raises(CoreError) as e_info:
        list(tree.demods["*"].child_nodes())
    assert e_info.value.args[0] == "Unrelated Error"


def test_subscribe(connection):
    tree = NodeTree(connection, "DEV1234")

    tree.demods[0].sample.subscribe()
    connection.subscribe.assert_called_once_with(tree.demods[0].sample.node_info.path)

    tree.demods[0].sample.unsubscribe()
    connection.unsubscribe.assert_called_once_with(tree.demods[0].sample.node_info.path)

    connection.subscribe.side_effect = RuntimeError()
    connection.unsubscribe.side_effect = RuntimeError()
    with pytest.raises(KeyError):
        tree.demods["*"].test.subscribe()
    with pytest.raises(KeyError):
        tree.demods["*"].test.unsubscribe()


def test_wait_for_state_change(connection):
    tree = NodeTree(connection, "DEV1234")

    sequence = iter([1] * 3 + [2] * 2)
    connection.getInt.side_effect = lambda node: next(sequence)
    connection.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [next(sequence)]}
    }
    tree.demods[0].trigger.wait_for_state_change(2)

    sequence = iter([1] * 3 + [2] * 2)
    value_enum1 = tree.demods[0].trigger.node_info.enum.trigin0_rising
    value_enum2 = tree.demods[0].trigger.node_info.enum.trigin0_falling
    tree.demods[0].trigger.wait_for_state_change(value_enum2)

    sequence = iter([1] * 3 + [2] * 2)
    tree.demods[0].trigger.wait_for_state_change("trigin0_falling")
    tree.demods[0].trigger.wait_for_state_change("trigger_input0_falling")

    connection.getInt.side_effect = lambda node: 2
    connection.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [2]}
    }
    tree.demods[0].trigger.wait_for_state_change(2)
    tree.demods[0].trigger.wait_for_state_change(value_enum2)
    tree.demods[0].trigger.wait_for_state_change("trigin0_falling")
    tree.demods[0].trigger.wait_for_state_change("trigger_input0_falling")

    connection.getInt.side_effect = lambda node: 1
    connection.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [1]}
    }
    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change(2, timeout=0.1)
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change to the "
        "expected value within 0.1s. 2 != 1"
    )

    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change(value_enum2, timeout=0.1)
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change to the "
        "expected value within 0.1s. 'trigin0_falling' != 'trigin0_rising'"
    )

    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change("trigin0_falling", timeout=0.1)
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change to the "
        "expected value within 0.1s. 'trigin0_falling' != 'trigin0_rising'"
    )

    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change(
            "trigger_input0_falling", timeout=0.1
        )
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change to the "
        "expected value within 0.1s. 'trigin0_falling' != 'trigin0_rising'"
    )

    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change(1, invert=True, timeout=0.1)
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change from the "
        "expected value 1 within 0.1s."
    )

    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change(
            value_enum1, invert=True, timeout=0.1
        )
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change from the "
        "expected value 'trigin0_rising' within 0.1s."
    )

    with pytest.raises(TimeoutError) as e:
        tree.demods[0].trigger.wait_for_state_change(
            "trigger_input0_rising", invert=True, timeout=0.1
        )
    assert (
        str(e.value) == "/dev1234/demods/0/trigger did not change from the "
        "expected value 'trigin0_rising' within 0.1s."
    )

    sequence = cycle([1] * 3 + [2])
    connection.getInt.side_effect = lambda node: next(sequence)
    connection.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [next(sequence)]}
    }
    tree.demods["*"].trigger.wait_for_state_change(2)

    with pytest.raises(KeyError) as e_info:
        tree.hello.wait_for_state_change(1)

    with pytest.raises(KeyError) as e_info:
        tree.hello["*"].test.wait_for_state_change(1)

    # Stale cache
    sequence = iter([1] * 3 + [0])
    stale_cache = True

    def get_side_effect(node, **kwargs):
        nonlocal stale_cache
        stale_cache = False
        return {node: {"timestamp": [0], "value": [next(sequence)]}}

    def get_int_side_effect(node, **kwargs):
        if stale_cache:
            pytest.fail("wait_for_state_change accessed a stale cache element!")
        return get_side_effect(node)[node]["value"][0]

    connection.getInt.side_effect = get_int_side_effect
    connection.get.side_effect = get_side_effect

    tree.demods[0].trigger.wait_for_state_change(0)

    # Verify the correct value has been fetched from the device
    # and it didn't stop early.
    with pytest.raises(StopIteration):
        next(sequence)

    with pytest.raises(KeyError) as e:
        tree.demods[0].trigger.wait_for_state_change("non_existant_key")

    # Numpy types
    sequence = iter([1] * 3 + [0])

    def get_side_effect(node, **kwargs):
        val = np.array([next(sequence)], dtype="longlong")
        return {node: {"timestamp": [0], "value": val}}

    def get_int_side_effect(node, **kwargs):
        return int(get_side_effect(node)[node]["value"][0])

    connection.getInt.side_effect = get_int_side_effect
    connection.get.side_effect = get_side_effect

    tree.demods[0].harmonic.wait_for_state_change(0)

    # Verify the correct value has been fetched from the device
    # and it didn't stop early.
    with pytest.raises(StopIteration):
        next(sequence)

    # Test with zero timeout
    connection.getInt.side_effect = lambda node: 2
    connection.get.side_effect = lambda node, **kwargs: {
        node: {"timestamp": [0], "value": [2]}
    }
    tree.demods[0].trigger.wait_for_state_change(2, timeout=0.0)


def test_nodetree_iterator(connection):
    tree = NodeTree(connection, "DEV1234")

    counter = 0
    for node, info in tree:
        assert node.node_info.path.lower() == info["Node"].lower()
        counter = counter + 1
    assert counter == len(tree._flat_dict)


def test_bool(connection):
    tree = NodeTree(connection, "DEV1234")
    assert bool(tree.demods[0].freq)
    assert not bool(tree.demods[0].req)


def test_len(connection):
    tree = NodeTree(connection, "DEV1234")
    assert len(tree.demods) == 4
    with pytest.raises(TypeError):
        len(tree.demods[0])


def test_hash_node(connection):
    tree = NodeTree(connection, "DEV1234")

    test_dict = {tree.demods[0].rate: 0, tree.demods[0].trigger: 1}

    assert test_dict[tree.demods[0].rate] == 0
    assert test_dict[tree.demods[0].trigger] == 1


def test_hash_node_info(connection):
    tree = NodeTree(connection, "DEV1234")

    test_dict = {tree.demods[0].rate.node_info: 0, tree.demods[0].trigger.node_info: 1}

    assert test_dict[tree.demods[0].rate.node_info] == 0
    assert test_dict[tree.demods[0].trigger.node_info] == 1


def test_eq_node_info(connection):
    tree = NodeTree(connection, "DEV1234")

    assert tree.demods[0].rate.node_info == tree["demods/0"].rate.node_info


def test_connection_dict(data_dir):
    data = {"/car/seat": 4, "/car/color": "blue", "/street/length": 110.4}
    json_path = data_dir / "nodedoc_fake.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = json.loads(file.read())
    connection = ConnectionDict(data, nodes_json)

    tree = NodeTree(connection)
    assert tree.car.seat() == 4
    assert tree.car.color() == "blue"
    assert tree.street.length() == 110.4

    tree.car.seat(5)
    assert tree.car.seat() == 5

    tree.street.length(1)
    assert tree.street.length() == 1.0
    assert tree.street.length(deep=True) == (None, 1.0)

    tree.car["*"](1)
    assert tree.car.seat() == 1
    assert tree.car.color() == "1"

    # subscribe and unsubscribe is not supported
    with pytest.raises(KeyError) as e_info:
        tree.car.seat.subscribe()
    with pytest.raises(KeyError) as e_info:
        tree.car.seat.unsubscribe()

    tree = NodeTree(connection, list_nodes=["/car/*"])
    assert tree.car.seat() == 1
    assert tree.car.color() == "1"
    with pytest.raises(KeyError):
        tree.street.length()

    connection.setVector("/car/seat", 5)
    assert tree.car.seat() == 5

    # Invalid initial values
    data = {"/car/seat": {2}, "/car/color": {"blue"}, "/street/length": {110.4}}
    connection = ConnectionDict(data, nodes_json)
    tree = NodeTree(connection)
    with pytest.raises(TypeError):
        tree.car.seat()
    assert tree.car.color() == "{'blue'}"
    with pytest.raises(TypeError):
        tree.street.length()


def test_connection_dict_set_list(data_dir):
    data = {"/car/seat": 4, "/car/color": "blue", "/street/length": 110.4}
    json_path = data_dir / "nodedoc_fake.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = json.loads(file.read())
    connection = ConnectionDict(data, nodes_json)
    connection.set([("/car/seat", 1), ("/car/color", "red")])
    assert {"/car/seat": 1, "/car/color": "red", "/street/length": 110.4} == data


def test_connection_dict_missing_node(data_dir):
    data = {"/car/seat": 4, "/car/color": "blue", "/street/length": 110.4}
    json_path = data_dir / "nodedoc_fake.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = json.loads(file.read())
    connection = ConnectionDict(data, nodes_json)
    with pytest.raises(KeyError):
        connection.set("/car/test", 5)


def test_connection_dict_callable_nodes(data_dir):
    global seat
    seat = 6

    def update_seat(value=None):
        global seat
        if value is None:
            return seat + 1
        seat = value + 1
        return None

    data = {"/car/seat": update_seat, "/car/color": "blue", "/street/length": 110.4}
    json_path = data_dir / "nodedoc_fake.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = json.loads(file.read())
    connection = ConnectionDict(data, nodes_json)
    tree = NodeTree(connection)
    assert tree.car.seat() == seat + 1

    tree.car.seat(10)
    assert seat == 11


@pytest.fixture()
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

    yield HDAWG("DEV1234", "HDAWG4", session)


def test_nodelist_is_node(connection, hdawg):
    nt = NodeTree(connection, "DEV1234")
    bar = NodeList([hdawg], nt, ("foobar",))
    assert bar[0] == hdawg
    assert bar == Node(nt, ("foobar",))


def test_nodelist_numpy(connection, hdawg):
    nt = NodeTree(connection, "DEV1234")
    bar = NodeList([hdawg, hdawg], nt, ("foobar",))
    for test_index in np.arange(2):
        assert bar[test_index] == hdawg


def test_nodelist_hash(connection, hdawg):
    nt = NodeTree(connection, "DEV1234")
    bar = NodeList([hdawg], nt, ("foobar",))
    hash(bar) == hash(Node(nt, ("foobar",)))


def test_resolve_wildcards_labone_single_ok():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("test/hello/world", paths) == ["test/hello/world"]


def test_resolve_wildcards_labone_single_fail():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("test/hello/a", paths) == []


def test_resolve_wildcards_labone_wildcard_middle_ok():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("test/*/there", paths) == [
        "test/hello/there",
        "test/hi/there",
    ]


def test_resolve_wildcards_labone_wildcard_middle_fail():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("test/*/you", paths) == []


def test_resolve_wildcards_labone_wildcard_partial_ok():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("test", paths) == [
        "test/hello/world",
        "test/hello/there",
        "test/hi/there",
    ]


def test_resolve_wildcards_labone_wildcard_partial_fail():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("tes", paths) == []


def test_resolve_wildcards_labone_wildcard_partial_subset():
    paths = [
        "/awgs/0/outputs/0/enables/0",
        "/awgs/1/outputs/0/enables/0",
        "/awgs/0/outputs/1/enables/0",
        "/awgs/0/enable",
        "/awgs/1/enable",
    ]
    assert resolve_wildcards_labone("/awgs/*/enable", paths) == [
        "/awgs/0/enable",
        "/awgs/1/enable",
    ]


def test_resolve_wildcards_labone_wildcard_end_ok():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("test/hello/*", paths) == [
        "test/hello/world",
        "test/hello/there",
    ]


def test_resolve_wildcards_labone_wildcard_end_fail():
    paths = ["test/hello/world", "test/hello/there", "test/hi/there"]
    assert resolve_wildcards_labone("new/hello/*", paths) == []


def test_garbage_collection_of_session(connection):
    gc.collect()

    def tester():
        tree = NodeTree(connection, "DEV1234")
        assert tree.demods[0].freq.is_valid()

    tester()
    gc.collect()
    for obj in gc.get_objects():
        assert not isinstance(obj, NodeTree)


def test_garbage_collection_of_session_node_info(connection):
    gc.collect()

    def tester():
        tree = NodeTree(connection, "DEV1234")
        assert not tree.demods[0].freq.node_info.is_setting

    tester()
    gc.collect()
    for obj in gc.get_objects():
        assert not isinstance(obj, NodeTree)


def test_node_info_caching(connection):
    tree = NodeTree(connection, "DEV1234")
    assert tree._node_infos == {}

    assert not tree.demods[0].freq.node_info.is_setting

    assert tree.demods[0].freq in tree._node_infos


class TestWildCardResult:
    @pytest.fixture()
    def node_tree(self, connection):
        tree = NodeTree(connection, "DEV1234")
        connection.get.return_value = OrderedDict(
            [
                (
                    "/dev1234/demods/0/rate",
                    {
                        "timestamp": array("q", [123]),
                        "value": array("d", [2]),
                    },
                ),
                (
                    "/dev1234/demods/1/rate",
                    {
                        "timestamp": array("q", [1234]),
                        "value": array("d", [3]),
                    },
                ),
            ]
        )
        return tree

    @pytest.fixture
    def wildcard_call_no_deep(self, node_tree):
        return node_tree.demods["*"].rate(deep=False)

    def test_call_no_deep(self, wildcard_call_no_deep):
        assert wildcard_call_no_deep == {
            "/dev1234/demods/0/rate": 2,
            "/dev1234/demods/1/rate": 3,
        }

    def test_repr(self, wildcard_call_no_deep):
        assert repr(wildcard_call_no_deep) == str(
            {"/dev1234/demods/0/rate": 2.0, "/dev1234/demods/1/rate": 3.0}
        )  # repr() displays here as float, but in Notebooks and prints it is int

    def test_getitem(self, wildcard_call_no_deep, node_tree):
        assert wildcard_call_no_deep[node_tree.demods[1].rate] == 3

    def test_assert_in(self, wildcard_call_no_deep, node_tree):
        assert node_tree.demods[1].rate in wildcard_call_no_deep

    def test_to_dict(self, wildcard_call_no_deep):
        assert wildcard_call_no_deep.to_dict() == {
            "/dev1234/demods/0/rate": 2,
            "/dev1234/demods/1/rate": 3,
        }

    def test_len(self, wildcard_call_no_deep):
        assert len(wildcard_call_no_deep) == 2

    def test_iter(self, wildcard_call_no_deep):
        assert list(iter(wildcard_call_no_deep)) == [
            "/dev1234/demods/0/rate",
            "/dev1234/demods/1/rate",
        ]

    def test_deepcopy(self, wildcard_call_no_deep):
        assert deepcopy(wildcard_call_no_deep) == {
            "/dev1234/demods/0/rate": 2,
            "/dev1234/demods/1/rate": 3,
        }

    def test_deep_wildcard(self, node_tree):
        data_wc = node_tree.demods["*"].rate(deep=True)
        assert data_wc == {
            "/dev1234/demods/0/rate": (123, 2),
            "/dev1234/demods/1/rate": (1234, 3),
        }

    def test_pickle_enum(self, node_tree, connection):
        connection.getInt.return_value = 0
        enum_value = node_tree.demods[0].trigger()
        new_enum_value = pickle.loads(pickle.dumps(enum_value))
        assert new_enum_value == enum_value
        for old, new in zip(type(enum_value), type(new_enum_value)):
            assert old == new
