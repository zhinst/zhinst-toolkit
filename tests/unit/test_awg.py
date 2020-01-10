import pytest
from hypothesis import given, assume, strategies as st

from drivers.awg import AWG
from drivers.awg import NotConnectedError, WaveformUploadError
from helpers import Waveform
import numpy as np


def test_init_awg():
    awg = AWG()
    assert awg.awg_module_executed == False


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
        awg.upload_waveform(Waveform([], []))
        awg.is_running


def test_waveform_error():
    awg = AWG()
    with pytest.raises(WaveformUploadError):
        awg.upload_waveform("blub")
