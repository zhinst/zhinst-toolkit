from . import HDAWG, UHFQA


class Factory(object):
    @classmethod
    def configure_device(cls, device):
        type_ = device.config.device_type
        dev = None
        if type_.lower() == "hdawg":
            dev = HDAWG(device)
        elif type_.lower() == "uhfqa":
            dev = UHFQA(device)
        else:
            # should never hit this
            raise Exception(f"unsupported device type! {type_}")

        return dev

