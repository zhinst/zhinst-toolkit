import numpy as np
import time

from helpers import Waveform
from controller import Controller


if __name__ == "__main__":

    hd = "hdawg0"
    qa = "uhfqa0"

    c = Controller()
    c.setup("resources/connection-hd-qa.json")
    c.connect_device(hd)
    c.connect_device(qa)

    # device settings
    c.set(
        qa,
        [
            ("/awgs/0/single", 1),
            ("/sigouts/0/on", 1),
            ("/awgs/0/triggers/*/channel", 2),
            ("/awgs/0/triggers/*/slope", 1),
        ],
    )
    c.set(
        hd,
        [
            ("/awgs/0/single", 1),
            ("/sigouts/0/on", 1),
            ("/system/clocks/referenceclock/source", 1),
        ],
    )

    # shared sequence parameters
    amps = np.linspace(0, 1, 101)
    reps = 100
    period = 50e-3

    # on HDAWG AWG1: send trigger, T1 sequence
    settings = dict(
        sequence_type="Rabi",
        trigger_mode="Send Trigger",
        pulse_amplitudes=amps,
        pulse_width=30e-9,
        pulse_truncation=3,
        period=period,
        repetitions=reps,
    )
    c.awg_set_sequence_params(hd, 0, **settings)
    c.awg_compile(hd, 0)

    # on AWG2: wait for trigger, play "Simple" sequence with ones on ch1
    settings = dict(
        sequence_type="Simple",
        trigger_mode="External Trigger",
        latency=160e-9,
        period=period,
        repetitions=reps * len(amps),
        clock_rate=1.8e9,
    )
    c.awg_set_sequence_params(qa, 0, **settings)
    c.awg_queue_waveform(qa, 0, Waveform(np.ones(2000), []))
    c.awg_upload_waveforms(qa, 0)

    # run AWGs
    c.awg_run(qa, 0)
    time.sleep(0.5)
    c.awg_run(hd, 0)

    print("Done!")
