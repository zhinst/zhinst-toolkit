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
    num_points = 101
    amps = np.linspace(0, 1, num_points)
    delays = np.logspace(-7, -5, num_points)
    reps = 1000
    period = 50e-6

    # on AWG2: wait for trigger, play "Simple" sequence with ones on ch1
    settings_simple = dict(
        sequence_type="Simple",
        trigger_mode="External Trigger",
        latency=100e-9,
        period=period,
        repetitions=reps * num_points,
    )
    c.awg_set_sequence_params(hd, awg1, **settings_simple)
    # queue waveform and upload
    c.awg_queue_waveform(hd, awg1, Waveform(np.ones(2000), []))
    c.awg_upload_waveforms(hd, awg1)

    # define settings for Rabi, T1, T2
    settings_rabi = dict(
        sequence_type="Rabi",
        trigger_mode="Send Trigger",
        pulse_amplitudes=amps,
        pulse_width=30e-9,
        pulse_truncation=4,
        period=period,
        repetitions=reps,
    )
    settings_t1 = dict(sequence_type="T1", delay_times=delays, pulse_amplitude=1.0)
    settings_t2 = dict(sequence_type="T2*", delay_times=delays, pulse_amplitude=1.0)

    for i in range(3):
        for settings in [settings_rabi, settings_t1, settings_t2]:
            c.awg_set_sequence_params(hd, awg0, **settings)
            c.awg_compile(hd, awg0)
            c.awg_run(hd, awg1)
            c.awg_run(hd, awg0)
            wait_awg_done(c, awg0, sleep=1)

    print("Done!")
