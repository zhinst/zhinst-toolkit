# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .context import MFLI, DeviceTypes


def test_init_uhfqa():
    mf = MFLI("name", "dev1234")
    assert mf.device_type == DeviceTypes.MFLI
