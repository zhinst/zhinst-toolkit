import numpy as np
import time

from helpers import Waveform
from controller import Controller


def wait_awg_done(c, awg, sleep=0.5):
    time.sleep(sleep)
    tik = time.time()
    while c.awg_is_running("hdawg0", awg):
        time.sleep(sleep)
        print(f"AWG {awg} running for {int(time.time() - tik)} s")
    time.sleep(sleep)


if __name__ == "__main__":

    hd = "hdawg0"

    c = Controller()
    c.setup("connection-hdawg.json")
    c.connect_device(hd, "dev8030")

    awg0 = 0
    awg1 = 1

    # basic device settings
    c.set(
        hd,
        [
            (f"/awgs/{awg1}/auxtriggers/*/slope", 1),  # trigger to Rise
            (f"/awgs/{awg1}/auxtriggers/*/channel", 2),  # Trigger In 3
            ("/awgs/*/single", 1),  # Rerun off
            ("/sigouts/0/on", 1),
            ("/sigouts/2/on", 1),
        ],
    )

    # shared sequence parameters
    reps = 1000
    period = 50e-6

    # on AWG2: wait for trigger, play "Simple" sequence with ones on ch1
    settings_master = dict(
        sequence_type="Simple",
        trigger_mode="Send Trigger",
        period=period,
        repetitions=reps,
    )
    settings_slave = dict(
        sequence_type="Simple",
        trigger_mode="External Trigger",
        latency=100e-9,
        period=period,
        repetitions=reps,
    )

    c.awg_set_sequence_params(hd, awg0, **settings_master)
    c.awg_set_sequence_params(hd, awg1, **settings_slave)

    x = np.linspace(-1, 1, 200)
    y1 = x
    y2 = np.sinc(5 * x)

    n = 250  # MAX. ~250 waveforms.... otherwise sporadic disconnects and waveform corruption!
    for i in range(n):
        c.awg_queue_waveform(hd, awg0, Waveform(i / n * y1, []))
        c.awg_queue_waveform(hd, awg1, Waveform((1 - i / n) * y2, []))

    c.awg_upload_waveforms(hd, awg0)
    c.awg_upload_waveforms(hd, awg1)

    c.awg_run(hd, awg1)
    c.awg_run(hd, awg0)
    wait_awg_done(c, awg0, sleep=1)

    print("Done!")
