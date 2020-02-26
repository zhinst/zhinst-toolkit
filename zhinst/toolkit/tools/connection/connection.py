import zhinst.ziPython as zi


class ZIDeviceConnection:
    def __init__(self, connection_details):
        self._connection_details = connection_details
        self._daq = None
        self._awg = None

    def connect(self):
        self._daq = zi.ziDAQServer(
            self._connection_details.host,
            self._connection_details.port,
            self._connection_details.api,
        )
        if self._daq is not None:
            print(
                f"Successfully connected to data server at "
                f"{self._connection_details.host}"
                f"{self._connection_details.port} "
                f"api version: {self._connection_details.api}"
            )
            self._awg = self.AWGModule(self._daq)
        else:
            print("No connection could be established...")

    def connect_device(self, **kwargs):
        if self._daq is None:
            raise Exception("No existing connection to data server")
        if not all(k for k in ["serial", "interface"]):
            raise Exception(
                "To connect a Zurich Instruments' device, youd need a serial and an interface [1gbe or usb]"
            )
        serial = kwargs.get("serial")
        interface = kwargs.get("interface")
        self._daq.connectDevice(serial, interface)
        print(
            f"Successfully connected to device {serial.upper()} on interface {interface.upper()}"
        )
        self._awg.update(device=serial, index=0)

    def set(self, *args):
        return self._daq.set(*args)

    def get(self, *args, **kwargs):
        return self._daq.get(*args, **kwargs)

    def list_nodes(self, *args, **kwargs):
        return self._daq.listNodesJSON(*args, **kwargs)

    class AWGModule:
        def __init__(self, daq):
            self._awgModule = daq.awgModule()
            self._awgModule.execute()
            self._device = self._awgModule.getString("/device")
            self._index = self._awgModule.getInt("/index")

        def set(self, *args, **kwargs):
            self.update(**kwargs)
            self._awgModule.set(*args)

        def get(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.get(*args, flat=True)

        def get_int(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.getInt(*args)

        def get_double(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.getDouble(*args)

        def get_string(self, *args, **kwargs):
            self.update(**kwargs)
            return self._awgModule.getString(*args)

        def update(self, **kwargs):
            if "device" in kwargs.keys():
                self._update_device(kwargs["device"])
            if "index" in kwargs.keys():
                self._update_index(kwargs["index"])

        def _update_device(self, device):
            if device != self.device:
                self._update_index(0)
                self._awgModule.set("/device", device)
                self._device = device

        def _update_index(self, index):
            if index != self.index:
                self._awgModule.set("/index", index)
                self._index = index

        @property
        def index(self):
            return self._index

        @property
        def device(self):
            return self._device

    @property
    def awg_module(self):
        return self._awg
