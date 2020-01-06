from drivers import HDAWG, UHFQA
import numpy as np
import time



if __name__ == "__main__":
    
    
    hd = HDAWG()
    hd.connect("dev8030")
    hd.set_node_value("sigouts/2/on", 1)
    hd.set_node_value("sigouts/3/on", 1)
    hd.set_node_value("awgs/1/single", 1)
    hd.setup_awg(1)

    qa = UHFQA()
    qa.connect("dev2266")
    qa.set_node_value("sigouts/1/on", 1)
    qa.set_node_value("awgs/0/single", 1)
    qa.setup_awg()

    # parameters for T1
    period = 0.01
    repetitions = 5
    t1_times = np.linspace(0, 60e-6, 350)
    repetitions_RO = repetitions * len(t1_times)


    # setup sequencers
    hd.awgs[1].set(
        sequence_type="T1",
        period=period,
        trigger_mode="Send Trigger",
        clock_rate=2.4e9,
        delay_times=t1_times,
        pulse_truncation=4,
        repetitions=repetitions
    )

    qa.awg.set(
        sequence_type="Simple",
        period=period,
        trigger_mode="External Trigger",
        clock_rate=1.8e9,
        repetitions=repetitions_RO
    )

    x = np.linspace(0, 180, 3200)
    w1 = np.sin(x)
    w2 = np.cos(x)
    qa.awg.add_waveform(w1, w2)

    
    hd.awgs[1].update()
    qa.awg.upload_waveforms()

    print(hd.awgs[1].sequence_params)
    print(qa.awg.sequence_params)

    qa.awg.run()
    time.sleep(1)
    hd.awgs[1].run()