import pytest
from hypothesis import given, assume, strategies as st
from pytest import fixture

from interface import InstrumentConfiguration
from controller.baseController import BaseController
from controller.drivers import connection
import json
import time


HD = "hdawg0"
QA = "uhfqa0"
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
    controller_hdawg.connect_device(HD)


def test_connect_device_uhfqa(controller_uhfqa):
    controller_uhfqa.connect_device(QA)


def test_get_set(controller_hdawg, controller_uhfqa):
    for c, name in zip([controller_hdawg, controller_uhfqa], [HD, QA]):
        c.connect_device(name)
        time.sleep(1)
        for v in c.get(name, "sigouts/*/on", valueonly=True):
            assert v == 0
        time.sleep(1)
        c.set(name, "sigouts/*/on", 1)
        for v in c.get(name, "sigouts/*/on", valueonly=True):
            assert v == 1
        time.sleep(1)
        c.set(name, "sigouts/*/on", 0)
        for v in c.get(name, "sigouts/*/on", valueonly=True):
            assert v == 0
        c.get(name, "sigouts/*/on", valueonly=False)
        c.get(name, "sigouts/0/on", valueonly=True)
        c.get(name, "zi/config/open", valueonly=True)
        c.set(name, {})


def test_get_set_list(controller_hdawg):
    c = controller_hdawg
    c.connect_device(HD)
    time.sleep(1)
    for v in c.get(HD, [f"sigouts/{i}/on" for i in range(8)], valueonly=True):
        assert v == 0
    time.sleep(1)
    c.set(HD, zip([f"sigouts/{i}/on" for i in range(8)], [1] * 8))
    for v in c.get(HD, [f"sigouts/{i}/on" for i in range(8)], valueonly=True):
        assert v == 1
    time.sleep(1)
    c.set(HD, zip([f"sigouts/{i}/on" for i in range(8)], [0] * 8))
    for v in c.get(HD, [f"sigouts/{i}/on" for i in range(8)], valueonly=True):
        assert v == 0


def test_get_set_errors(controller_hdawg):
    c = controller_hdawg
    with pytest.raises(Exception):
        c.set(HD, "sigouts/0/on", 1)
    with pytest.raises(Exception):
        c.get(HD, "sigouts/0/on")
    c.connect_device(HD)
    time.sleep(1)
    with pytest.raises(Exception):
        c.set(HD, ["invalid", "number", "of arguments"])
    with pytest.raises(Exception):
        c.set(HD, [("invalid", "number", "of arguments")])
    with pytest.raises(Exception):
        c.get(HD, {})

