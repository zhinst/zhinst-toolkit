import pytest
from hypothesis import given, assume, strategies as st

from drivers.awg import AWG
from drivers.awg import NotConnectedError, WaveformUploadError
from helpers import Waveform
import numpy as np


def test_init_awg():
    awg = AWG()
    assert awg.awg_module_executed == False
    assert awg.queue == []


def test_setup_awg_error():
    awg = AWG()
    with pytest.raises(TypeError):
        awg.setup("tst", "dev8030")


def test_not_connected_error():
    awg = AWG()
    with pytest.raises(NotConnectedError):
        awg.run()
        awg.stop()
        awg.upload_program("Test")
        awg.queue_waveform(Waveform([], []))
        awg.upload_waveforms()
        awg.is_running
        

