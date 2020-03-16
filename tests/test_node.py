import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import Node, NodeList


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


class Parent:
    _device = "device"


def test_node_init():
    node = Node(Parent())
    assert node._device == "device"
    assert len(node.nodes) == 0
    assert len(node.parameters) == 0


def test_repr():
    node = Node(Parent())
    assert node.__repr__() != ""


def test_init_submodules():
    node = Node(Parent())
    node._init_subnodes_recursively(node, DUMMY_DICT)
    print(node)
    assert node.nodes != []
    assert node.parameters != []
    assert len(node.first.parameters) == 3
    assert isinstance(node.second, NodeList)
    assert not isinstance(node.fourth, NodeList)
