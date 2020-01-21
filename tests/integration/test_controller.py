import pytest
from hypothesis import given, assume, strategies as st
from pytest import fixture

from interface import InstrumentConfiguration
from controller import Controller
from helpers import Waveform
import numpy as np
import json
import time


HD = "hdawg0"
QA = "uhfqa0"
SERIAL = "dev8030"
SERIAL_QA = "dev2266"
INTERFACE = "1gbe"


@fixture()
def controller():
    controller = Controller()
    controller.setup("resources/connection-hd-qa.json")
    yield controller
    del controller


def test_connect_device_hdawg(controller):
    controller.connect_device(HD)


def test_connect_device_uhfqa(controller):
    controller.connect_device(QA)


def test_compile_proram(controller):
    controller.connect_device(HD)
    controller.connect_device(QA)

    controller.awg_set_sequence_params(
        HD,
        0,
        sequence_type="Rabi",
        trigger_mode="Send Trigger",
        period=1,
        pulse_width=100e-9,
        repetitions=100,
    )
    controller.awg_set_sequence_params(
        QA,
        0,
        sequence_type="Rabi",
        trigger_mode="External Trigger",
        period=1,
        pulse_width=100e-9,
        repetitions=100,
    )
    controller.awg_compile(HD, 0)
    controller.awg_compile(QA, 0)


def test_change_sequence_types(controller):
    controller.connect_device(HD)
    controller.connect_device(QA)
    for t in ["Rabi", "T1", "T2*"]:
        controller.awg_set_sequence_params(HD, 0, sequence_type=t)
        controller.awg_set_sequence_params(QA, 0, sequence_type=t)
        controller.awg_compile(HD, 0)
        controller.awg_compile(QA, 0)


def test_waveform_upload(controller):
    controller.connect_device(HD)
    controller.connect_device(QA)
    controller.awg_set_sequence_params(HD, 0, sequence_type="Simple")
    controller.awg_set_sequence_params(HD, 1, sequence_type="Simple")
    controller.awg_set_sequence_params(QA, 0, sequence_type="Simple")
    for i in range(10):
        w = Waveform(np.ones(800), -np.ones(800))
        controller.awg_queue_waveform(HD, 0, w)
        controller.awg_queue_waveform(HD, 1, w)
        controller.awg_queue_waveform(QA, 0, w)
    controller.awg_upload_waveforms(HD, 0)
    controller.awg_upload_waveforms(HD, 1)
    controller.awg_upload_waveforms(QA, 0)




