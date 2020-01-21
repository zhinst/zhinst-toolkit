from dataclasses import dataclass

from marshmallow import Schema, fields, post_load, EXCLUDE


class ZIDIOConfig(Schema):
    device = fields.Str()

    @dataclass
    class Data:
        device: str

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIAWGChannelConfig(Schema):
    wave = fields.Str(allow_none=True)
    trig = fields.Str(allow_none=True)
    marker = fields.Str(allow_none=True)

    @dataclass
    class Data:
        wave: str = None
        trig: str = None
        marker: str = None

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIAWGConfig(Schema):
    iq = fields.Boolean()

    @dataclass
    class Data:
        iq: bool

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIAWG(Schema):
    awg = fields.Integer()
    config = fields.Nested(ZIAWGConfig)
    ch0 = fields.Nested(ZIAWGChannelConfig)
    ch1 = fields.Nested(ZIAWGChannelConfig)

    @dataclass
    class Data:
        awg: int
        config: ZIAWGConfig.Data
        ch0: ZIAWGChannelConfig.Data
        ch1: ZIAWGChannelConfig.Data

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIDEVICEIO(Schema):
    awgs = fields.List(fields.Nested(ZIAWG))
    dio = fields.Nested(ZIDIOConfig)

    @dataclass
    class Data:
        awgs: ZIAWG.Data
        dio: ZIDIOConfig.Data

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIDeviceConfig(Schema):
    serial = fields.Str()
    device_type = fields.Str()
    interface = fields.Str()

    @dataclass
    class Data:
        serial: str
        device_type: str
        interface: str

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIDevice(Schema):
    name = fields.Str()
    config = fields.Nested(ZIDeviceConfig)
    connectivity = fields.Nested(ZIDEVICEIO)

    @dataclass
    class Data:
        name: str
        config: ZIDeviceConfig.Data
        connectivity: ZIDEVICEIO.Data

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class Instrument(Schema):
    provider = fields.Str()
    setup = fields.List(fields.Nested(ZIDevice))

    @dataclass
    class Data:
        provider: str
        setup: ZIDevice.Data

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class ZIAPI(Schema):
    host = fields.Str()
    port = fields.Integer()
    api = fields.Integer()

    class Meta:
        fields = ("host", "port", "api")
        unknown = EXCLUDE

    @dataclass
    class Data:
        host: str
        port: int
        api: int
        name: str = None

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class API(Schema):
    provider = fields.Str()
    details = fields.Nested(ZIAPI)

    @dataclass
    class Data:
        provider: str
        details: ZIAPI.Data

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)


class InstrumentConfiguration(Schema):
    class Meta:
        fields = ("api_configs", "instruments")
        unknown = EXCLUDE

    @dataclass
    class Data:
        api_configs: API.Data
        instruments: Instrument.Data

    api_configs = fields.List(fields.Nested(API))
    instruments = fields.List(fields.Nested(Instrument))

    @post_load
    def make_(self, data, **kwargs):
        return self.Data(**data)
