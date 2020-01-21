import numpy as np
import time

from helpers import Waveform
from controller import Controller


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
            ("/awgs/*/single", 0),  # Rerun
            ("/sigouts/0/on", 1),
            ("/sigouts/2/on", 1),
        ],
    )

    # shared sequence parameters
    amps = np.linspace(0, 1, 101)
    reps = 10000
    period = 1e-3

    # on AWG1: send trigger, Rabi sequence
    settings = dict(
        sequence_type="Rabi",
        trigger_mode="Send Trigger",
        pulse_amplitudes=amps,
        pulse_width=30e-9,
        pulse_truncation=4,
        period=period,
        repetitions=reps,
    )
    c.awg_set_sequence_params(hd, awg0, **settings)
    c.awg_compile(hd, awg0)

    # on AWG2: wait for trigger, play "Simple" sequence with ones on ch1
    settings = dict(
        sequence_type="Simple",
        trigger_mode="External Trigger",
        latency=100e-9,
        period=period,
        repetitions=reps * len(amps),
    )
    c.awg_set_sequence_params(hd, awg1, **settings)
    # queue waveform and upload
    c.awg_queue_waveform(hd, awg1, Waveform(np.ones(2000), []))
    c.awg_upload_waveforms(hd, awg1)

    # run AWGs, slave first
    c.awg_run(hd, awg1)
    c.awg_run(hd, awg0)

    print("Done!")
