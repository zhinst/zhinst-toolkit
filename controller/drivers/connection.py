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
            self.__awg = self.AWGModule(self.__daq)
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

    def set(self, *args):
        self.__daq.set(*args)

    def get(self, *args, **kwargs):
        return self.__daq.get(*args, **kwargs)

    class AWGModule:
        def __init__(self, daq):
            self.__awgModule = daq.awgModule()
            self.__awgModule.execute()
            self.__index = self.__awgModule.getInt("/index")
            self.__device = self.__awgModule.getString("/device")

        def set(self, *args, **kwargs):
            self.update(**kwargs)
            self.__awgModule.set(*args)

        def get(self, *args, **kwargs):
            self.update(**kwargs)
            return self.__awgModule.get(*args, flat=True)

        def get_int(self, *args, **kwargs):
            self.update(**kwargs)
            return self.__awgModule.getInt(*args)

        def get_double(self, *args, **kwargs):
            self.update(**kwargs)
            return self.__awgModule.getDouble(*args)

        def get_string(self, *args, **kwargs):
            self.update(**kwargs)
            return self.__awgModule.getString(*args)

        def update(self, **kwargs):
            if "index" in kwargs.keys():
                self.__update_index(kwargs["index"])
            if "device" in kwargs.keys():
                self.__update_device(kwargs["device"])

        def __update_index(self, index):
            if index != self.index:
                self.__awgModule.set("/index", index)
                self.__index = index

        def __update_device(self, device):
            if device != self.device:
                self.__awgModule.set("/device", device)
                self.__device = device

        @property
        def index(self):
            return self.__index

        @property
        def device(self):
            return self.__device

    @property
    def awgModule(self):
        return self.__awg
