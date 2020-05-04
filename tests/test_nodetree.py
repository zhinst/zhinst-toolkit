import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import NodeTree, Node, NodeList


DUMMY_PARAMETER = {
    "Node": "test/bla/blub",
}

DUMMY_DICT = {
    "first": {
        "first": DUMMY_PARAMETER,
        "second": DUMMY_PARAMETER,
        "third": DUMMY_PARAMETER,
    },
    "second": {1: DUMMY_PARAMETER, 2: DUMMY_PARAMETER, 3: DUMMY_PARAMETER,},
    "third": DUMMY_PARAMETER,
    "fourths": {1: DUMMY_PARAMETER},
}

FLAT_DUMMY_DICT = {
    "first/first": DUMMY_PARAMETER,
    "first/second": DUMMY_PARAMETER,
    "first/third": DUMMY_PARAMETER,
    "second/1": DUMMY_PARAMETER,
    "second/2": DUMMY_PARAMETER,
    "second/3": DUMMY_PARAMETER,
    "third": DUMMY_PARAMETER,
    "fourths/1": DUMMY_PARAMETER,
}


class Device:
    serial = ""

    def _get_nodetree(self, *args):
        return FLAT_DUMMY_DICT


class Parent:
    def __init__(self, dev):
        self._device = dev


def test_node_init():
    dev = Device()
    parent = Parent(dev)
    node = Node(parent)
    assert node._parent == parent
    assert node._device == dev
    assert len(node.nodes) == 0
    assert len(node.parameters) == 0


def test_repr():
    node = Node(Parent(Device()))
    assert node.__repr__() != ""


def test_init_submodules():
    node = Node(Parent(Device()))
    node._init_subnodes_recursively(node, DUMMY_DICT)
    print(node)
    assert node.nodes != []
    assert node.parameters != []
    assert len(node.first.parameters) == 3
    assert isinstance(node.second, NodeList)
    assert not isinstance(node.fourth, NodeList)


def test_nodetree_init():
    dev = Device()
    tree = NodeTree(dev)
    assert tree._nodetree_dict == DUMMY_DICT
    assert tree.__repr__() != ""


@given(st.integers(0, 10))
def test_nodelist_init(n):
    lst = NodeList()
    [lst.append(0) for i in range(n)]
    assert len(lst) == n
    assert lst.__repr__() != ""
    if n > 0:
        assert f"Node {n}" in lst.__repr__()

