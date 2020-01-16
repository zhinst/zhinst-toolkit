from helpers import Waveform
from controller import Controller
from controller.drivers.connection import ZIDeviceConnection
import numpy as np
import time


if __name__ == "__main__":

    c = Controller()
    c.setup("resources/connection.json")
    c.connect_device("hdawg0")

    # c.awg_set_sequence_params(0, sequence_type="Rabi")
    # c.compile_program(0)

    c.awg_set_sequence_params(0, sequence_type="Simple")

    n = 100
    for i in range(n):
        wave = i / n * np.ones(1000)
        c.awg_queue_waveform(0, Waveform(wave, wave))

    c.awg_upload_waveforms(0)

    print("Done!")
