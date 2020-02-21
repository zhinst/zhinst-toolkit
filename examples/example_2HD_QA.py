import numpy as np
import time

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ziDrivers.controller import Controller


if __name__ == "__main__":

    hd1 = "hdawg0"
    hd2 = "hdawg1"
    qa = "uhfqa0"

    qa_awg = (qa, 0)
    trigger_awg = (hd1, 0)
    slave_awgs = [ 
        (hd1, 1), 
        (hd1, 2), 
        (hd1, 3), 
        (hd2, 0), 
        (hd2, 1), 
        (hd2, 2), 
        (hd2, 3) 
    ]

    slave_delays = [
        0,
        0, 
        0, 
        0,
        0,
        0,
        0,
    ]



    c = Controller()
    c.setup("connection-2hd-qa.json")
    c.connect_device(qa, "dev2266", "1GbE")
    c.connect_device(hd1, "dev8030", "1GbE")
    c.connect_device(hd2, "dev8022", "1GbE")
    

    # device settings
    qa_settings = [
            ("/awgs/0/single", 1),
            ("/sigouts/0/on", 1),
            ("/awgs/0/triggers/*/channel", 2),
            ("/awgs/0/triggers/*/slope", 1),
        ]

    hd_settings = [
            ("/awgs/*/single", 1),
            #("/sigouts/*/on", 1),
            ("/system/clocks/referenceclock/source", 1),
        ]
    
    c.set(qa, qa_settings)
    c.set(hd1, hd_settings)
    c.set(hd2, hd_settings)

    # turn on only needed output
    for i, on in enumerate([0, 0, 1, 0, 0, 0, 0, 0]):
        c.set(hd1, f"/sigouts/{i}/on", on)
    for i, on in enumerate([1, 0, 0, 0, 0, 0, 1, 0]):
        c.set(hd2, f"/sigouts/{i}/on", on)

    # trigger
    for awg in slave_awgs:
        c.set(awg[0], f"/awgs/{awg[1]}/auxtriggers/*/channel", 2 * awg[1])
        c.set(awg[0], f"/awgs/{awg[1]}/auxtriggers/*/slope", 1)     # rise



    # shared sequence parameters
    reps = 100000
    period = 10e-3

    # sequence settings
    readout_sequence_params = dict(
        sequence_type       =   "Readout",
        trigger_mode        =   "External Trigger",
        period              =   period,
        repetitions         =   reps,
        readout_frequencies =   np.linspace(87e6, 136e6, 5),
        readout_amplitudes   =   [1.0] * 5,
        readout_length      =   2e-6,
        #trigger_delay       =   -100e-9,
    )

    trigger_sequence_params = dict(
        sequence_type   =   "Simple",
        trigger_mode    =   "Send Trigger",
        period          =   period,
        repetitions     =   reps,
    )

    awg_sequence_params = dict(
        sequence_type   =   "Rabi",
        trigger_mode    =   "External Trigger",
        period          =   period,
        repetitions     =   reps,
        pulse_amplitudes=   [1.0],    #np.linspace(0, 1.0, 101),
        pulse_width     = 100e-9,
    )

    print(f"awg: {qa_awg}")
    c.awg_set_sequence_params(*qa_awg, **readout_sequence_params)
    
    print(f"awg: {trigger_awg}")
    c.awg_set_sequence_params(*trigger_awg, **trigger_sequence_params)
    
    for awg in slave_awgs:
        print(f"awg: {awg}")
        c.awg_set_sequence_params(*awg, **awg_sequence_params)

    for awg, delay in zip(slave_awgs, slave_delays):
        c.awg_set_sequence_params(*awg, trigger_delay=0)


    # compilation
    print(f"awg: {qa_awg}")
    c.awg_compile(*qa_awg)
    
    print(f"awg: {trigger_awg}")
    c.awg_queue_waveform(*trigger_awg, data=([], [])) # play zeros x 32
    c.awg_compile(*trigger_awg)
    c.awg_upload_waveforms(*trigger_awg)

    for awg in slave_awgs:
        print(f"awg: {awg}")
        # c.awg_queue_waveform(*awg, data=(np.ones(100), np.ones(100)))
        c.awg_compile(*awg)
        # c.awg_upload_waveforms(*awg)
    
    
    # run AWGs
    c.awg_run(*qa_awg)
    for awg in slave_awgs:
        c.awg_run(*awg)
    
    time.sleep(1)
    c.awg_run(*trigger_awg)

    print("Done!")