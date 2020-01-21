import pytest
from hypothesis import given, assume, strategies as st
from pytest import fixture
import json
import time

from .context import ziDrivers


HD = "hdawg0"
QA = "uhfqa0"
SERIAL = "dev8030"
SERIAL_QA = "dev2266"
INTERFACE = "1gbe"


@fixture()
def controller_hdawg():
    controller = ziDrivers.baseController.BaseController()
    controller.setup("connection-hdawg.json")
    yield controller
    del controller


@fixture()
def controller_uhfqa():
    controller = ziDrivers.baseController.BaseController()
    controller.setup("connection-uhfqa.json")
    yield controller
    del controller


def test_connect_device_hdawg(controller_hdawg):
    controller_hdawg.connect_device(HD, SERIAL)


def test_connect_device_uhfqa(controller_uhfqa):
    controller_uhfqa.connect_device(QA, SERIAL_QA)


def test_get_set_hd(controller_hdawg):
    c = controller_hdawg
    c.connect_device(HD, SERIAL)
    time.sleep(1)
    for v in c.get(HD, "sigouts/*/on", valueonly=True):
        assert v == 0
    time.sleep(1)
    c.set(HD, "sigouts/*/on", 1)
    for v in c.get(HD, "sigouts/*/on", valueonly=True):
        assert v == 1
    time.sleep(1)
    c.set(HD, "sigouts/*/on", 0)
    for v in c.get(HD, "sigouts/*/on", valueonly=True):
        assert v == 0
    c.get(HD, "sigouts/*/on", valueonly=False)
    c.get(HD, "sigouts/0/on", valueonly=True)
    c.get(HD, "zi/config/open", valueonly=True)
    c.set(HD, {})


def test_get_set_qa(controller_uhfqa):
    c = controller_uhfqa
    c.connect_device(QA, SERIAL_QA)
    time.sleep(1)
    for v in c.get(QA, "sigouts/*/on", valueonly=True):
        assert v == 0
    time.sleep(1)
    c.set(QA, "sigouts/*/on", 1)
    for v in c.get(QA, "sigouts/*/on", valueonly=True):
        assert v == 1
    time.sleep(1)
    c.set(QA, "sigouts/*/on", 0)
    for v in c.get(QA, "sigouts/*/on", valueonly=True):
        assert v == 0
    c.get(QA, "sigouts/*/on", valueonly=False)
    c.get(QA, "sigouts/0/on", valueonly=True)
    c.get(QA, "zi/config/open", valueonly=True)
    c.set(QA, {})


def test_get_set_list(controller_hdawg):
    c = controller_hdawg
    c.connect_device(HD, SERIAL)
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
    c.connect_device(HD, SERIAL)
    time.sleep(1)
    with pytest.raises(Exception):
        c.set(HD, ["invalid", "number", "of arguments"])
    with pytest.raises(Exception):
        c.set(HD, [("invalid", "number", "of arguments")])
    with pytest.raises(Exception):
        c.get(HD, {})

