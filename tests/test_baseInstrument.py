# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import pytest

from .context import (
    BaseInstrument,
    DeviceTypes,
    ziDiscovery,
    baseinstrument_logger,
)

baseinstrument_logger.disable_logging()


class DiscoveryMock:
    def find(self, serial):
        return serial.lower()

    def get(self, serial):
        assert serial == serial.lower()
        return {"deviceid": serial}


class ConnectionMock:
    def __init__(self):
        self.established = True

    def connect_device(self, serial=None, interface=None):
        pass

    def list_nodes(self, *args, **kwargs):
        return (
            '{"node_address": '
            '{"Node": "node_address", '
            '"Description": "description" }}'
        )

    def get(self, *args, **kwargs):
        return {"node": {"value": [""]}}


def test_init_instrument():
    instr = BaseInstrument(
        "name",
        DeviceTypes.PQSC,
        "dev10000",
        interface="1GbE",
        discovery=DiscoveryMock(),
    )
    assert instr._nodetree is None
    assert instr._options is None
    assert instr.nodetree is None
    assert instr.name == "name"
    assert instr.device_type == DeviceTypes.PQSC
    assert instr.serial == "dev10000"
    assert instr.interface == "1GbE"
    assert instr.is_connected is False
    assert instr.options is None


def test_check_connection():
    instr = BaseInstrument(
        "name",
        DeviceTypes.PQSC,
        "dev10000",
        interface="1GbE",
        discovery=DiscoveryMock(),
    )
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._check_connected()
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._check_node_exists("sigouts/0/on")
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr.connect_device()
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._get("sigouts/0/on")
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._set("sigouts/0/on", 1)
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._get_node_dict("sigouts/0/on")
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._get_node_dict("zi/about/revision")
    with pytest.raises(baseinstrument_logger.ToolkitConnectionError):
        instr._get_streamingnodes()


def test_serials():
    with pytest.raises(baseinstrument_logger.ToolkitError):
        BaseInstrument(
            "name", DeviceTypes.PQSC, None, interface="1GbE", discovery=DiscoveryMock()
        )
    with pytest.raises(baseinstrument_logger.ToolkitError):
        BaseInstrument(
            "name", DeviceTypes.PQSC, 10000, interface="1GbE", discovery=DiscoveryMock()
        )
    BaseInstrument(
        "name",
        DeviceTypes.PQSC,
        "dev10000",
        interface="1GbE",
        discovery=DiscoveryMock(),
    )
    BaseInstrument(
        "name",
        DeviceTypes.PQSC,
        "DEV10000",
        interface="1GbE",
        discovery=DiscoveryMock(),
    )


def test_serial_normalization():
    inst = BaseInstrument(
        "name",
        DeviceTypes.PQSC,
        "DEV10000",
        interface="1GbE",
        discovery=DiscoveryMock(),
    )
    inst.setup(ConnectionMock())
    inst.connect_device()
    assert inst.serial == "dev10000"


def test_default_discovery():
    inst = BaseInstrument("name", DeviceTypes.PQSC, "DEV10000", interface="1GbE")
    assert isinstance(inst._controller.discovery, ziDiscovery)
