import numpy as np
import time

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ziDrivers import Controller


def wait_awg_done(c, awg, sleep=0.5):
    time.sleep(sleep)
    # tik = time.time()
    while c.awg_is_running("hdawg0", awg):
        time.sleep(sleep)
        # print(f"AWG {awg} running for {int(time.time() - tik)} s")
    time.sleep(sleep)


if __name__ == "__main__":

    hd = "hdawg0"

    c = Controller()
    c.setup("connection-hdawg.json")
    c.connect_device(hd, "dev8030")

    awg = 0

    # basic device settings
    c.set(hd, [("/awgs/*/single", 1), ("/sigouts/0/on", 1)])

    # shared sequence parameters
    reps = 10000
    period = 200e-6

    # on AWG2: wait for trigger, play "Simple" sequence with ones on ch1
    settings = dict(
        sequence_type="Simple",
        trigger_mode="Send Trigger",
        period=period,
        repetitions=reps,
    )
    c.awg_set_sequence_params(hd, awg, **settings)

    length = 80000
    x = np.linspace(-1, 1, length)
    y1 = x

    c.awg_queue_waveform(hd, awg, data=(y1, y1))
    c.awg_compile_and_upload_waveforms(hd, awg)
    c.awg_run(hd, awg)
    wait_awg_done(c, awg, sleep=0.05)

    for n in range(1):
        for i in range(20):
            c.awg_replace_waveform(hd, awg, data=(i / 20 * y1, (1 - i / 20) * y1))
            c.awg_upload_waveforms(hd, awg)
            c.awg_run(hd, awg)
            wait_awg_done(c, awg, sleep=0.05)

    print("Done!")
