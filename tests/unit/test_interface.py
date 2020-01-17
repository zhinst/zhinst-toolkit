import pytest
from hypothesis import given, assume, strategies as st

from interface import InstrumentConfiguration
import json


def test_json_hdawg():
    instrument_config = "resources/connection-hdawg.json"
    with open(instrument_config) as file:
        data = json.load(file)
        schema = InstrumentConfiguration()
        schema.load(data)


def test_json_uhfqa():
    instrument_config = "resources/connection-uhfqa.json"
    with open(instrument_config) as file:
        data = json.load(file)
        schema = InstrumentConfiguration()
        schema.load(data)
