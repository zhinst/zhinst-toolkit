from drivers import HDAWG, UHFQA
import numpy as np
import time



if __name__ == "__main__":
    
    # set device parameters
    hd = HDAWG()
    hd.connect("dev8030")
    hd.set([
        ("sigouts/2/on", 1),
        ("sigouts/3/on", 1),
        ("awgs/1/single", 1),
        ("awgs/1/outputs/1/amplitude", 0.25)
    ])
    hd.setup_awg(1)

    qa = UHFQA()
    qa.connect("dev2266")
    qa.set([
        ("sigouts/1/on", 1),
        ("awgs/0/single", 1)
    ])
    qa.setup_awg()

    # set sequence parameters
    period = 0.01
    repetitions = 5
    rabi_amplitudes = np.linspace(0, 1.0, 200)
    repetitions_RO = repetitions * len(rabi_amplitudes)

    hd.awgs[1].set(
        sequence_type="Rabi",
        period=period,
        trigger_mode="Send Trigger",
        clock_rate=hd.get("system/clocks/sampleclock/freq", valueonly=True),
        pulse_amplitudes=rabi_amplitudes,
        pulse_width=20e-9,
        pulse_truncation=4,
        repetitions=repetitions
    )
    hd.awgs[1].update()

    qa.awg.set(
        sequence_type="Simple",
        period=period,
        trigger_mode="External Trigger",
        clock_rate=1.8e9,
        repetitions=repetitions_RO
    )
    x = np.linspace(0, 180, 3200)
    qa.awg.add_waveform(np.sin(x), np.cos(x))
    qa.awg.upload_waveforms()
    
    print(hd.awgs[1].sequence_params)
    print(qa.awg.sequence_params)

    # qa.awg.run()
    # time.sleep(1)
    # hd.awgs[1].run()