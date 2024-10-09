"""Module for all device drivers."""
import typing as t

from zhinst.toolkit.driver.devices.base import BaseInstrument
from zhinst.toolkit.driver.devices.hdawg import HDAWG
from zhinst.toolkit.driver.devices.pqsc import PQSC
from zhinst.toolkit.driver.devices.qhub import QHub
from zhinst.toolkit.driver.devices.shfqa import SHFQA
from zhinst.toolkit.driver.devices.shfsg import SHFSG
from zhinst.toolkit.driver.devices.uhfli import UHFLI
from zhinst.toolkit.driver.devices.uhfqa import UHFQA

from zhinst.toolkit.driver.devices.shfqc import SHFQC  # isort:skip

DeviceType = t.Union[
    BaseInstrument, HDAWG, PQSC, QHub, SHFQA, SHFSG, UHFLI, UHFQA, SHFQC
]

DEVICE_CLASS_BY_MODEL = {
    "SHFQC": SHFQC,
    "SHFQA4": SHFQA,
    "SHFQA2": SHFQA,
    "SHFSG4": SHFSG,
    "SHFSG8": SHFSG,
    "HDAWG4": HDAWG,
    "HDAWG8": HDAWG,
    "PQSC": PQSC,
    "QHUB": QHub,
    "UHFQA": UHFQA,
    "UHFLI": UHFLI,
    "UHFAWG": UHFLI,
}

__all__ = [
    "DeviceType",
    "DEVICE_CLASS_BY_MODEL",
    "BaseInstrument",
    "HDAWG",
    "PQSC",
    "QHub",
    "SHFQA",
    "SHFSG",
    "UHFLI",
    "UHFQA",
    "SHFQC",
]
