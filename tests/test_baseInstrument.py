import pytest
from hypothesis import given, assume, strategies as st
from hypothesis.stateful import rule, precondition, RuleBasedStateMachine
import numpy as np

from .context import BaseInstrument, ZHTKException


def init_instrument():
    instr = BaseInstrument("name", "pqsc", "dev1234", interface="1GbE")
    assert instr.nodetree is None
    assert instr.name == "name"
    assert instr.device_type == "pqsc"
    assert instr.serial == "dev1234"
    assert instr.interface == "1GbE"
    assert instr.is_connected == False


def check_connection():
    instr = BaseInstrument("name", "pqsc", "dev1234", interface="1GbE")
    with pytest.raises(ZHTKException):
        instr._check_connected()
    with pytest.raises(ZHTKException):
        instr.connect_device()
    with pytest.raises(ZHTKException):
        instr._get("sigouts/0/on")
    with pytest.raises(ZHTKException):
        instr._set("sigouts/0/on", 1)
