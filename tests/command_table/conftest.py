import json
import pytest
from pathlib import Path

from zhinst.toolkit.command_table import CommandTable


CT_SCHEMA_22_02 = Path(__file__).parent / "data/command_table_schema_22_02.json"
CT_SCHEMA_22_08 = Path(__file__).parent / "data/command_table_schema_22_08.json"


@pytest.fixture(scope="function")
def command_table_completed():
    """L1 22.02"""
    with open(Path(__file__).parent / "data/command_table_completed.json") as f:
        data = json.load(f)
    yield data


@pytest.fixture(scope="module")
def command_table_schema_22_02():
    """L1 22.02"""
    with open(CT_SCHEMA_22_02) as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def command_table_schema_22_08():
    """L1 22.08"""
    with open(CT_SCHEMA_22_08) as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module", params=[CT_SCHEMA_22_02, CT_SCHEMA_22_08])
def command_table_schema(request):
    with open(request.param) as f:
        data = json.load(f)
    return data


@pytest.fixture
def command_table(command_table_schema):
    yield CommandTable(command_table_schema)
