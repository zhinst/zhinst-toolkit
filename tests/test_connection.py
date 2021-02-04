import pytest
import zhinst.ziPython as zi


from .context import (
    ZIConnection,
    DeviceConnection,
    ToolkitConnectionError,
    DeviceTypes,
)

from zhinst.toolkit.control.connection import (
    AWGModuleConnection,
    DAQModuleConnection,
    SweeperModuleConnection,
)


class Details:
    host = "something"
    port = 1234
    api = 5


class Config:
    _api_config = Details()


class Device:
    _config = Config()
    serial = "dev###"
    interface = "usb"
    device_type = DeviceTypes.HDAWG


class DiscoveryMock:
    def find(self, serial):
        return serial.upper()

    def get(self, serial):
        assert serial == serial.upper()
        return {"deviceid": serial}


def test_init_zi_connection():
    c = ZIConnection(Details())
    assert not c.established
    assert c._daq is None
    assert c._awg is None


def test_check_connection():
    c = ZIConnection(Details())
    with pytest.raises(ToolkitConnectionError):
        c.connect_device()
    with pytest.raises(ToolkitConnectionError):
        c.get("tests/test")
    with pytest.raises(ToolkitConnectionError):
        c.get_sample("tests/test")
    with pytest.raises(ToolkitConnectionError):
        c.set("tests/test", 1)
    with pytest.raises(ToolkitConnectionError):
        c.set_vector("tests/test", [0])
    with pytest.raises(ToolkitConnectionError):
        c.connect()


def test_ZIConnection_daq_api(mocker):
    daq_mock = mocker.Mock(spec=zi.ziDAQServer)
    mocker.patch("zhinst.ziPython.ziDAQServer", return_value=daq_mock)
    c = ZIConnection(Details())
    c.connect()

    c.set("tests/test", [0])
    daq_mock.set.assert_called_with("tests/test", [0])

    c.get("tests/test", [0])
    daq_mock.get.assert_called_with("tests/test", [0])

    c.list_nodes("tests/test", [0])
    daq_mock.listNodesJSON.assert_called_with("tests/test", [0])

    c.get_sample("tests/test", [0])
    daq_mock.getSample.assert_called_with("tests/test", [0])

    c.set_vector("tests/test", [0])
    daq_mock.setVector.assert_called_with("tests/test", [0])


def test_ZIConnection_properties(mocker):
    daq_mock = mocker.Mock(spec=zi.ziDAQServer)
    mocker.patch("zhinst.ziPython.ziDAQServer", return_value=daq_mock)
    c = ZIConnection(Details())
    c.connect()

    assert type(c.awg_module) == AWGModuleConnection
    assert type(c.daq_module) == DAQModuleConnection
    assert type(c.sweeper_module) == SweeperModuleConnection


def test_AWGModuleConnection(mocker):
    awg_module_mock = mocker.Mock()
    attrs = {"awgModule.return_value": awg_module_mock}
    daq_mock = mocker.Mock(spec=zi.ziDAQServer, **attrs)

    awg_module = AWGModuleConnection(daq_mock)

    awg_module.set("tests/test", [0])
    awg_module_mock.set.assert_called_with("tests/test", [0])

    awg_module.get("tests/test", [0])
    awg_module_mock.get.assert_called_with("tests/test", [0], flat=True)

    awg_module.get_int("tests/test", [0])
    awg_module_mock.getInt.assert_called_with("tests/test", [0])

    awg_module.get_double("tests/test", [0])
    awg_module_mock.getDouble.assert_called_with("tests/test", [0])

    awg_module.get_string("tests/test", [0])
    awg_module_mock.getString.assert_called_with("tests/test", [0])


@pytest.mark.parametrize("with_device", [True, False])
def test_DAQModuleConnection(mocker, with_device: bool):
    daq_module_mock = mocker.Mock()
    attrs = {"dataAcquisitionModule.return_value": daq_module_mock}
    daq_mock = mocker.Mock(spec=zi.ziDAQServer, **attrs)
    device = mocker.Mock() if with_device is True else None

    daq_module = DAQModuleConnection(daq_mock)

    daq_module.execute(device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.execute.assert_called()
    daq_module_mock.reset_mock()

    daq_module.finish(device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.finish.assert_called()
    daq_module_mock.reset_mock()

    daq_module.finished(device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.finished.assert_called()
    daq_module_mock.reset_mock()

    daq_module.progress(device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.progress.assert_called()
    daq_module_mock.reset_mock()

    daq_module.trigger(device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.trigger.assert_called()
    daq_module_mock.reset_mock()

    daq_module.read(device, foo=True)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.read.assert_called_with(foo=True)
    daq_module_mock.reset_mock()

    daq_module.subscribe(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.subscribe.assert_called_with(True)
    daq_module_mock.reset_mock()

    daq_module.unsubscribe(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.unsubscribe.assert_called_with(True)
    daq_module_mock.reset_mock()

    daq_module.save(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.save.assert_called_with(True)
    daq_module_mock.reset_mock()

    daq_module.clear(device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.clear.assert_called()
    daq_module_mock.reset_mock()

    daq_module.set(True, device=device)
    if with_device:
        assert daq_module_mock.set.call_count == 2
        daq_module.update_device(None)
    else:
        daq_module_mock.set.assert_called_with(True)

    daq_module_mock.reset_mock()

    daq_module.get(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.get.assert_called_with(True, flat=True)
    daq_module_mock.reset_mock()

    daq_module.get_int(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.getInt.assert_called_with(True)
    daq_module_mock.reset_mock()

    daq_module.get_double(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.getDouble.assert_called_with(True)
    daq_module_mock.reset_mock()

    daq_module.get_string(True, device=device)
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.getString.assert_called_with(True)
    daq_module_mock.reset_mock()

    daq_module_mock.listNodesJSON.return_value = '{"foo": true}'
    daq_module.get_nodetree("tests/test", device=device, **{"foo": True})
    if with_device:
        daq_module_mock.set.assert_called_with("/device", device)
        daq_module.update_device(None)
    daq_module_mock.listNodesJSON.assert_called_with("tests/test", foo=True)
    daq_module_mock.reset_mock()


def test_init_device_connection():
    dev = Device()
    c = DeviceConnection(dev, DiscoveryMock())
    assert c._connection is None
    assert c._device == dev


def test_device_connection_connect():
    c = DeviceConnection(Device(), DiscoveryMock())
    with pytest.raises(ToolkitConnectionError):
        c.setup()
    with pytest.raises(ToolkitConnectionError):
        c.setup(connection=ZIConnection(Details()))
    with pytest.raises(ToolkitConnectionError):
        c.connect_device()
    with pytest.raises(ToolkitConnectionError):
        c.get("tests/test")
    with pytest.raises(ToolkitConnectionError):
        c.set("tests/test", 1)
    with pytest.raises(ToolkitConnectionError):
        c.get_nodetree("*")


def test_device_normalized_serial():
    c = DeviceConnection(Device(), DiscoveryMock())
    assert c.normalized_serial is None
