# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .context import UHFLI, DeviceTypes


def test_init_uhfqa():
    li = UHFLI("name", "dev1234")
    assert li.device_type == DeviceTypes.UHFLI
