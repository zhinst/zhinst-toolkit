import pytest
from hypothesis import given, assume, strategies as st
from pytest import fixture

from interface import InstrumentConfiguration
from controller.baseController import BaseController
from controller.drivers import connection
import json
import time


SERIAL = "dev8030"
SERIAL_QA = "dev2266"
INTERFACE = "1gbe"


@fixture()
def controller_hdawg():
    controller = BaseController()
    controller.setup("resources/connection-hdawg.json")
    yield controller
    del controller


@fixture()
def controller_uhfqa():
    controller = BaseController()
    controller.setup("resources/connection-uhfqa.json")
    yield controller
    del controller


def test_connect_device_hdawg(controller_hdawg):
    controller_hdawg.connect_device("hdawg0")


def test_connect_device_uhfqa(controller_uhfqa):
    controller_uhfqa.connect_device("uhfqa0")


def test_get_set(controller_hdawg, controller_uhfqa):
    for c, name in zip([controller_hdawg, controller_uhfqa], ["hdawg0", "uhfqa0"]):
        c.connect_device(name)
        time.sleep(1)
        for v in c.get("sigouts/*/on", valueonly=True):
            assert v == 0
        time.sleep(1)
        c.set("sigouts/*/on", 1)
        for v in c.get("sigouts/*/on", valueonly=True):
            assert v == 1
        time.sleep(1)
        c.set("sigouts/*/on", 0)
        for v in c.get("sigouts/*/on", valueonly=True):
            assert v == 0
        c.get("sigouts/*/on", valueonly=False)
        c.get("sigouts/0/on", valueonly=True)
        c.get("zi/config/open", valueonly=True)
        c.set({})


def test_get_set_list(controller_hdawg):
    c = controller_hdawg
    c.connect_device("hdawg0")
    time.sleep(1)
    for v in c.get([f"sigouts/{i}/on" for i in range(8)], valueonly=True):
        assert v == 0
    time.sleep(1)
    c.set(zip([f"sigouts/{i}/on" for i in range(8)], [1] * 8))
    for v in c.get([f"sigouts/{i}/on" for i in range(8)], valueonly=True):
        assert v == 1
    time.sleep(1)
    c.set(zip([f"sigouts/{i}/on" for i in range(8)], [0] * 8))
    for v in c.get([f"sigouts/{i}/on" for i in range(8)], valueonly=True):
        assert v == 0


def test_get_set_errors(controller_hdawg):
    c = controller_hdawg
    with pytest.raises(Exception):
        c.set("sigouts/0/on", 1)
    with pytest.raises(Exception):
        c.get("sigouts/0/on")
    c.connect_device("hdawg0")
    time.sleep(1)
    with pytest.raises(Exception):
        c.set(["invalid", "number", "of arguments"])
    with pytest.raises(Exception):
        c.set([("invalid", "number", "of arguments")])
    with pytest.raises(Exception):
        c.get({})

