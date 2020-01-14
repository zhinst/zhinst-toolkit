from controller import Controller
from controller.drivers.connection import ZIDeviceConnection
import numpy as np
import time


if __name__ == "__main__":

    class Details:
        def __init__(self):
            self.host = "localhost"
            self.port = 8004
            self.api = 6

    c = ZIDeviceConnection(Details())
    c.connect()

    print(c.awgModule.get("*"), index=1)

    # c = Controller()
    # c.setup("resources/connection.json")
    # c.connect_device("hdawg0")

    # c.set("sigouts/0/on", 1)
    # time.sleep(3)
    # c.set("sigouts/0/on", 0)
