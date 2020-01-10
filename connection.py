import abc
from enum import Enum

import zhinst.ziPython as zi


class DeviceManufacturer(Enum):
    ZI = 1,
    ANAPICO = 2

    @staticmethod
    def from_string(type_: str):
        if type_ == 'zi':
            return DeviceManufacturer.ZI


class ConnectionFactory(object):

    @staticmethod
    def create(type_, **kwargs):
        if type_ == DeviceManufacturer.ZI:
            return ZIDeviceConnection(**kwargs)


class DeviceConnection(metaclass=abc.ABCMeta):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def connect_device(self, **kwargs):
        pass


class ZIDeviceConnection(DeviceConnection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__daq = None

    def connect(self):
        self.__daq = zi.ziDAQServer(self.host, self.port, self.api)
        if self.__daq is not None:
            print(f"Successfully connected to data server at {self.host}:{self.port} api version: {self.api}")

    def connect_device(self, **kwargs):
        if self.__daq is None:
            raise Exception("No existing connection to data server")
        if not all(k for k in ['serial', 'interface']):
            raise Exception(
                'To connect a Zurich Instruments\' device, youd need a serial and an interface [1gbe or usb]')
        serial = kwargs.get('serial')
        interface = kwargs.get('interface')
        self.__daq.connectDevice(serial, interface)
        print(f"Successfully connected device {serial} to data server using {interface} interface")
