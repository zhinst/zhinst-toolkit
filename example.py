from controller import Controller
import numpy as np
import time


if __name__ == "__main__":

    c = Controller()
    c.setup("resources/connection.json")
    c.connect_device("hdawg0")

    c.set("sigouts/0/on", 1)
    time.sleep(3)
    c.set("sigouts/0/on", 0)

