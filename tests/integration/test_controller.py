# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
from pytest import fixture

from .context import ziDrivers
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
    controller = ziDrivers.Controller()
    controller.setup("connection-hd-qa.json")
    yield controller
    del controller


def test_connect_device_hdawg(controller):
    controller.connect_device(HD, SERIAL)


def test_connect_device_uhfqa(controller):
    controller.connect_device(QA, SERIAL_QA)


def test_compile_proram(controller):
    controller.connect_device(HD, SERIAL)
    controller.connect_device(QA, SERIAL_QA)

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
    controller.connect_device(HD, SERIAL)
    controller.connect_device(QA, SERIAL_QA)
    for t in ["Rabi", "T1", "T2*"]:
        controller.awg_set_sequence_params(HD, 0, sequence_type=t)
        controller.awg_set_sequence_params(QA, 0, sequence_type=t)
        controller.awg_compile(HD, 0)
        controller.awg_compile(QA, 0)


def test_waveform_upload(controller):
    controller.connect_device(HD, SERIAL)
    controller.connect_device(QA, SERIAL_QA)
    controller.awg_set_sequence_params(HD, 0, sequence_type="Simple")
    controller.awg_set_sequence_params(HD, 1, sequence_type="Simple")
    controller.awg_set_sequence_params(QA, 0, sequence_type="Simple")
    for i in range(10):
        w = (np.ones(800), -np.ones(800))
        controller.awg_queue_waveform(HD, 0, data=w)
        controller.awg_queue_waveform(HD, 1, data=w)
        controller.awg_queue_waveform(QA, 0, data=w)
    controller.awg_compile_and_upload_waveforms(HD, 0)
    controller.awg_compile_and_upload_waveforms(HD, 1)
    controller.awg_compile_and_upload_waveforms(QA, 0)

