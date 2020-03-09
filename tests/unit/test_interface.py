# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest
from hypothesis import given, assume, strategies as st
import json

from .context import InstrumentConfiguration


def test_json_hdawg():
    instrument_config = "ziDrivers/resources/connection-hdawg.json"
    with open(instrument_config) as file:
        data = json.load(file)
        schema = InstrumentConfiguration()
        schema.load(data)


def test_json_uhfqa():
    instrument_config = "ziDrivers/resources/connection-uhfqa.json"
    with open(instrument_config) as file:
        data = json.load(file)
        schema = InstrumentConfiguration()
        schema.load(data)
