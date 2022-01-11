import pytest
from unittest.mock import MagicMock
from collections import OrderedDict
from array import array
from numpy import array as nparray
from pathlib import Path
import json
from zhinst.toolkit.nodetree import Node, NodeTree

@pytest.fixture()
def data_dir(request):
    yield Path(request.fspath).parent / "data"

@pytest.fixture()
def connection(data_dir):

    json_path = data_dir / "nodedoc_dev1234.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()

    connection = MagicMock()
    connection.listNodesJSON.return_value = nodes_json
    yield connection


class TestNodeTree:
    def test_init(self, connection, data_dir):
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
            tree = NodeTree(connection_broken)
        assert "Leading slash not found" in e_info.value.args[0]

    def test_init_preloaded_json(self, data_dir):
        json_path = data_dir / "nodedoc_dev1234.json"
        with json_path.open("r", encoding="UTF-8") as file:
            nodes_json = json.loads(file.read())
        connection = MagicMock()  # plain mock without json info
        tree = NodeTree(connection, prefix_hide="DEV1234", preloaded_json=nodes_json)
        assert tree.prefix_hide == "dev1234"
        connection.listNodesJSON.mock_object.assert_not_called()

    def test_node_contains(self, connection):
        tree = NodeTree(connection, "DEV1234")

        assert "rate" in tree.demods[0] # existing child node
        assert "invalid" not in tree.demods[0] # non existing child node
        assert "node" not in tree.demods[0] # property

    def test_node_iter(self, connection):
        tree = NodeTree(connection, "DEV1234")

        childs = []
        for child, info in tree.demods[0]:
            childs.append(child)
            assert child.node == info["Node"]

        assert all([child.raw_tree[-1] in tree.demods[0] for child in childs])


    def test_node_access(self, connection):
        tree = NodeTree(connection, "DEV1234")

        # test local variable
        assert not tree._test
        assert not tree.demods._test
        # test attribute vs item
        assert tree.demods == tree["demods"]
        assert tree.demods == tree["/demods"]
        assert tree.demods.test == tree["demods/test"]

        # buildin keywords are escaped with tailing underscore
        assert tree.in_.test == tree["in/test"]
        assert tree.test.and_ == tree["test/and"]

        # test invalid nodes
        assert tree.no.real.element.raw_tree == ("no", "real", "element")
        assert str(tree.no.real.element) == "/dev1234/no/real/element"
        with pytest.raises(KeyError) as e_info:
            tree.no.real.element()
        assert e_info.value.args[0] == str(tree.no.real.element)

    def test_node(self, connection):
        tree = NodeTree(connection, "DEV1234")
        # test properties of node
        assert tree.demods[0].rate.node
        assert tree.demods[0].rate.description
        assert tree.demods[0].rate.type
        assert tree.demods[0].rate.unit
        assert tree.demods[0].trigger.options.get("1")

        # dir of nested node
        assert "append" in dir(tree.demods)  # test for list
        assert "rate" in dir(tree.demods[0])

    def test_get_cached(self, connection):
        tree = NodeTree(connection, "DEV1234")

        tree.demods[0].adcselect()
        connection.getInt.assert_called_with(tree.demods[0].adcselect.node)
        tree.demods[0].rate()
        connection.getDouble.assert_called_with(tree.demods[0].rate.node)
        tree.features.serial()
        connection.getString.assert_called_with(tree.features.serial.node)

        # Complex Double
        tree.update_node("demods/0/rate", {"Type": "Complex Double"})
        tree.demods[0].rate()
        connection.getComplex.assert_called_with(tree.demods[0].rate.node)
        connection.getComplex = None
        with pytest.raises(AttributeError) as e_info:
            tree.demods[0].rate()

        # ZIVectorData
        tree.system.impedance.calib.user.data()
        connection.get.assert_called_with(
            tree.system.impedance.calib.user.data.node, settingsonly=False, flat=True
        )

        # ZIDemodSample
        tree.demods[0].sample()
        connection.getSample.assert_called_with(tree.demods[0].sample.node)
        connection.getSample = None
        with pytest.raises(AttributeError) as e_info:
            tree.demods[0].sample()

        # ZIDIOSample
        tree.dios[0].input()
        connection.getDIO.assert_called_with(tree.dios[0].input.node)

    def test_get_deep(self, connection):
        tree = NodeTree(connection, "DEV1234")

        tree.demods[0].rate(deep=True)
        connection.get.assert_called_with(
            tree.demods[0].rate.node, settingsonly=False, flat=True
        )
        tree.demods[0].rate(deep=True, test=True)
        connection.get.assert_called_with(
            tree.demods[0].rate.node, settingsonly=False, flat=True, test=True
        )
        # overwrite internaly used kwarg
        tree.demods[0].rate(deep=True, settingsonly=True)
        connection.get.assert_called_with(
            tree.demods[0].rate.node, settingsonly=True, flat=True
        )

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
                        "timestamp": array("l", [1236389131550]),
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
            [("/dev1234/demods/0/rate", nparray([1674.10717773]))]
        )
        data = tree.demods[0].sample(deep=True)
        assert data == 1674.10717773

    def test_get_wildcard(self, connection):
        tree = NodeTree(connection, "DEV1234")

        connection.get.return_value = OrderedDict(
            [
                (
                    "/dev1234/demods/0/impedance",
                        {
                            "timestamp": array("l",[3880906635]),
                            "value": array("l", [123]),
                        },
                )
            ]
        )
        result = tree.demods()
        assert result[tree.demods[0].impedance] == (3880906635,123)
        connection.get.assert_called_with('/dev1234/demods/*', flat=True)

        # nested dict
        result = tree.demods(flat=False)
        assert isinstance(result, OrderedDict)

        # invalid node
        with pytest.raises(KeyError) as e_info:
            tree.invalid()

        # HF2 support
        connection.get.return_value = OrderedDict(
            [
                (
                    "/dev1234/demods/0/impedance",
                    nparray([125])
                )
            ]
        )
        result = tree.demods()
        assert result[tree.demods[0].impedance] == (None,125)
        connection.get.assert_called_with('/dev1234/demods/*', flat=True)


    def test_set(self, connection):
        tree = NodeTree(connection, "DEV1234")
        tree.demods[0].rate(22.0)
        connection.set.assert_called_with(tree.demods[0].rate.node, 22.0)
        tree.demods[0].rate(22.0, test=True)
        connection.set.assert_called_with(tree.demods[0].rate.node, 22.0, test=True)

        # sync set of nodes is only dependend on the input parameter not the
        # type of the node iself
        tree.demods[0].rate(22.0, deep=True)
        connection.syncSetDouble.assert_called_with(tree.demods[0].rate.node, 22.0)
        tree.demods[0].rate(0, deep=True)
        connection.syncSetInt.assert_called_once_with(tree.demods[0].rate.node, 0)
        tree.demods[0].rate("test", deep=True)
        connection.syncSetString.assert_called_once_with(
            tree.demods[0].rate.node, "test"
        )
        with pytest.raises(Exception) as e_info:
            tree.demods[0].rate(complex(2, -3), deep=True)

        tree.system.impedance.calib.user.data(b"Test Binary Data")
        connection.setVector.assert_called_once_with(
            tree.system.impedance.calib.user.data.node, b"Test Binary Data"
        )

        connection.setVector = None
        with pytest.raises(Exception) as e_info:
            tree.system.impedance.calib.user.data(b"Test Binary Data")

        connection.syncSetString = None
        tree.demods[0].rate("test", deep=True)
        connection.set.assert_called_with(tree.demods[0].rate.node, "test")

    def test_transactional_set(self, connection):
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
            tree.add_to_set_transaction("demods/0/phaseshift", 2)
        connection.set.assert_called_with(
            [("/dev1234/demods/0/rate", 22.0), ("/dev1234/demods/0/phaseshift", 2)]
        )

        with pytest.raises(AttributeError) as e_info:
            with tree.set_transaction():
                tree.system.impedance.calib.user.data(b"Test Binary Data")

        with pytest.raises(AttributeError) as e_info:
            tree.add_to_set_transaction("demods/0/phaseshift", 2)



    def test_get_node_info(self, connection):
        tree = NodeTree(connection, "DEV1234")
        # raw get
        assert tree.get_node_info("demods/0/rate") == tree.get_node_info(tree.demods[0].rate)
        assert tree.get_node_info("/dev1234/demods/0/rate") == tree.get_node_info(tree.demods[0].rate)
        assert tree.get_node_info("zi/config/open") == tree.get_node_info(tree.zi.config.open)
        assert tree.get_node_info("/zi/config/open") == tree.get_node_info(tree.zi.config.open)
        with pytest.raises(KeyError) as e_info:
            tree.get_node_info("/demods/0/rate")
        assert e_info.value.args[0] == "/demods/0/rate"
        with pytest.raises(ValueError):
            tree.get_node_info("dev1234/demods/0/rate")
        with pytest.raises(KeyError) as e_info:
            tree.get_node_info("no/real/element")
        assert e_info.value.args[0] == "/dev1234/no/real/element"

        # raw get wildcards
        assert tree.get_node_info("demods/*/rate") == tree.get_node_info(
            "demods/?/rate"
        )
        assert len(tree.get_node_info("demods/0/*")) > 1
        with pytest.raises(KeyError) as e_info:
            tree.get_node_info("demods/0/real/*")
        assert e_info.value.args[0] == "/dev1234/demods/0/real/*"
        with pytest.raises(KeyError) as e_info:
            tree.get_node_info("demod/0/*")
        assert e_info.value.args[0] == "/dev1234/demod/0/*"

    def test_update_node(self, connection):
        tree = NodeTree(connection, "DEV1234")

        tree.update_node("demods/0/rate", {"Unit": "test"})
        assert tree.demods[0].rate.unit == "test"
        tree.update_node("demods/0/rate", {"Test": "test"})
        assert tree.get_node_info("demods/0/rate").get("Test", None) == "test"
        tree.update_node("demods/0/rate", {"Unit": "test2", "Test2": True})
        assert tree.demods[0].rate.unit == "test2"
        assert tree.get_node_info("demods/0/rate").get("Test2", None)

        # new Node
        with pytest.raises(KeyError) as e_info:
            tree.update_node("test", {"Node": "test"})
        assert e_info.value.args[0] == "/dev1234/test"

        assert str(tree.test) == "/dev1234/test"
        tree.update_node("test", {"Node": "test"}, add=True)
        assert str(tree.test) == "test"

        assert str(tree.demods[0].test) == "/dev1234/demods/0/test"
        tree.update_node("demods/0/test", {"Node": "test"}, add=True)
        assert str(tree.demods[0].test) == "test"
        # tree.update_node("demods/0/test", {"Type": "Unknown", "Properties":"Read, Write"}, add=True)
        # with pytest.raises(Exception) as e_info:
        #     tree.demods[0].test(0, deep = True)

        tree.update_node("demods/0/rate", {"Properties": "Write"})
        with pytest.raises(Exception) as e_info:
            tree.demods[0].rate()
        tree.update_node("demods/0/rate", {"Properties": "Read"})
        with pytest.raises(Exception) as e_info:
            tree.demods[0].rate(12)

    def test_update_nodes(self, connection):
        tree = NodeTree(connection, "DEV1234")

        tree.update_nodes(
            {"demods/0/rate": {"Unit": "test"}, "demods/0/order": {"Unit": "test2"}}
        )
        assert tree.demods[0].rate.unit == "test"
        assert tree.demods[0].order.unit == "test2"

        with pytest.raises(KeyError) as e_info:
            tree.update_nodes(
                {"demods/0/rate": {"Unit": "test3"}, "test": {"Node": "test"}}
            )
        assert tree.demods[0].rate.unit == "test3"
        tree.update_nodes(
            {"demods/0/rate": {"Unit": "test3"}, "test": {"Node": "test4"}}, add=True
        )
        assert tree.test.node == "test4"

    def test_options(self, connection):
        tree = NodeTree(connection, "DEV1234")

        tree.demods[0].trigger("continuous")
        connection.set.assert_called_with(tree.demods[0].trigger.node, 0)

        tree.demods[0].trigger("continuou")
        connection.set.assert_called_with(tree.demods[0].trigger.node, "continuou")

        connection.getInt.return_value = 0
        assert tree.demods[0].trigger() == "continuous"

        connection.getInt.return_value = 12345678
        assert tree.demods[0].trigger() == 12345678

    def test_parser(self, connection):
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
        connection.set.assert_called_with(tree.demods[0].rate.node, 10)

    def test_subscribe(self, connection):
        tree = NodeTree(connection, "DEV1234")

        tree.demods[0].sample.subscribe()
        connection.subscribe.assert_called_once_with(tree.demods[0].sample.node)

        tree.demods[0].sample.unsubscribe()
        connection.unsubscribe.assert_called_once_with(tree.demods[0].sample.node)

    def test_wait_for_state_change(self, connection):
        tree = NodeTree(connection, "DEV1234")

        connection.getInt.side_effect = [1] * 3 + [2] * 2
        assert tree.demods[0].trigger.wait_for_state_change(2)
        connection.getInt.side_effect = None

        connection.getInt.return_value = 2
        assert tree.demods[0].trigger.wait_for_state_change(2)

        connection.getInt.return_value = 1
        assert not tree.demods[0].trigger.wait_for_state_change(2, timeout=0.5)

    def test_nodetree_iterator(self, connection):
        tree = NodeTree(connection, "DEV1234")

        counter = 0
        for node, info in tree:
            assert node.node == info["Node"]
            counter = counter + 1
        assert counter == len(tree._flat_dict)

    def test_hash_node(self, connection):
        tree = NodeTree(connection, "DEV1234")

        test_dict = {tree.demods[0].rate: 0, tree.demods[0].trigger: 1}

        assert test_dict[tree.demods[0].rate] == 0
        assert test_dict[tree.demods[0].trigger] == 1
