import abc
import zhinst.ziPython as zi


class DeviceConnection(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def connect_device(self, **kwargs):
        pass


class ZIDeviceConnection(DeviceConnection):
    def __init__(self, connection_details):
        self.__connection_details = connection_details
        self.__daq = None
        self.__awg = None

    def connect(self):
        self.__daq = zi.ziDAQServer(
            self.__connection_details.host,
            self.__connection_details.port,
            self.__connection_details.api,
        )
        if self.__daq is not None:
            print(
                f"Successfully connected to data server at "
                f"{self.__connection_details.host}"
                f"{self.__connection_details.port} "
                f"api version: {self.__connection_details.api}"
            )
        else:
            print("No connection could be established...")

    def connect_device(self, **kwargs):
        if self.__daq is None:
            raise Exception("No existing connection to data server")
        if not all(k for k in ["serial", "interface"]):
            raise Exception(
                "To connect a Zurich Instruments' device, youd need a serial and an interface [1gbe or usb]"
            )
        serial = kwargs.get("serial")
        interface = kwargs.get("interface")
        self.__daq.connectDevice(serial, interface)
        print(
            f"Successfully connected to device {serial.upper()} on interface {interface.upper()}"
        )

    def awg_init(self):
        self.__awg = self.__daq.awgModule()
        self.__awg.execute()

    def awg_set(self, *args, **kwargs):
        if self.__awg is not None:
            self.__awg.set(*args, **kwargs)
        else:
            raise Exception("AWG Module not initialized yet!")

    def awg_get(self, *args, **kwargs):
        if self.__awg is not None:
            return self.__awg.get(*args, **kwargs)
        else:
            raise Exception("AWG Module not initialized yet!")

    def awg_getInt(self, *args, **kwargs):
        if self.__awg is not None:
            return self.__awg.getInt(*args, **kwargs)
        else:
            raise Exception("AWG Module not initialized yet!")

    def awg_getDouble(self, *args, **kwargs):
        if self.__awg is not None:
            return self.__awg.getDouble(*args, **kwargs)
        else:
            raise Exception("AWG Module not initialized yet!")

    def awg_getString(self, *args, **kwargs):
        if self.__awg is not None:
            return self.__awg.getString(*args, **kwargs)
        else:
            raise Exception("AWG Module not initialized yet!")

    def set(self, *args, **kwargs):
        self.__daq.set(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.__daq.get(*args, **kwargs)

