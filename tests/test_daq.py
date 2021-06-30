import pytest

from .context import DAQModule, daq_logger

daq_logger.disable_logging()


class Parent:
    def _get_streamingnodes(self):
        return "streamingnodes"


def test_daq_init():
    p = Parent()
    daq = DAQModule(p)
    assert daq._parent == p
    assert daq._module is None
    assert not daq.signals
    assert not daq.results
    assert daq._signal_sources == "streamingnodes"
    assert daq._signal_types


def test_no_connection():
    p = Parent()
    daq = DAQModule(p)
    with pytest.raises(daq_logger.ToolkitConnectionError):
        daq._init_settings()
    with pytest.raises(daq_logger.ToolkitConnectionError):
        daq._set("endless", 0)
    with pytest.raises(daq_logger.ToolkitConnectionError):
        daq._get("endless")
