# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest

from .context import SweeperModule, sweeper_logger

sweeper_logger.disable_logging()


class Parent:
    def _get_streamingnodes(self):
        return "streamingnodes"


def test_sweeper_init():
    p = Parent()
    s = SweeperModule(p)
    assert s._parent == p
    assert s._module is None
    assert not s.signals
    assert not s.results
    assert s._signal_sources == "streamingnodes"
    assert not s._sweep_params


def test_no_connection():
    p = Parent()
    s = SweeperModule(p)
    with pytest.raises(sweeper_logger.ToolkitConnectionError):
        s._init_settings()
    with pytest.raises(sweeper_logger.ToolkitConnectionError):
        s._set("endless", 0)
    with pytest.raises(sweeper_logger.ToolkitConnectionError):
        s._get("endless")
