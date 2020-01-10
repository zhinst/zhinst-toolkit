# -----------------------------------------------------------------------------
# @copyright Copyright (c) 2019 Zurich Instruments AG - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# @author hossein.ajallooiean@zhinst.com
# @date
# -----------------------------------------------------------------------------


from enum import Enum

import networkx as nx

from . import HDAWG, UHFQA


class DeviceType(Enum):
    PQSC = 1
    HDAWG = 2
    UHFQA = 3
    LAST = 4


class Factory(object):
    @classmethod
    def get_device_type(cls, type_: str) -> DeviceType:
        if type_ == "pqsc":
            return DeviceType.PQSC
        elif type_ == "hdawg":
            return DeviceType.HDAWG
        elif type_ == "uhfqa":
            return DeviceType.UHFQA
        else:
            return DeviceType.LAST

    @classmethod
    def configure_device(cls, **kwargs):
        type_ = Factory.get_device_type(kwargs["properties"]["config"]["type"])
        dev = None
        if type_ == DeviceType.PQSC:
            raise Exception("PQSC not implemented...")
        elif type_ == DeviceType.HDAWG:
            dev = HDAWG(**kwargs)
        elif type_ == DeviceType.UHFQA:
            dev = UHFQA(**kwargs)
        else:
            raise Exception(f"unsupported device type! {type_}")

        return dev.graph, dev.labels

    @staticmethod
    def create(file):
        graph = nx.DiGraph()
        labels = {}
        for name, properties in file.items():
            device_graph, device_labels = Factory.configure_device(
                name=name, properties=properties
            )
            labels.update(device_labels)
            graph = nx.compose(graph, device_graph)
        return graph, labels
