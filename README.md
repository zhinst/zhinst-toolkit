# zi-driver

See examples for more ...

### `example_Rabi-T1-T2.py`:

Loops over Rabi, T1 and T2* sequence.

```python
c = Controller()

....

amps = np.linspace(0, 1, num_points)
delays = np.logspace(-7, -5, num_points)
reps = 1000
period = 50e-6

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
        c.awg_set_sequence_params(awg0, **settings)
        c.awg_compile(awg0)
        c.awg_run(awg1)
        c.awg_run(awg0)
        wait_awg_done(c, awg0, sleep=1)

```

### `example_waveform_upload.py`:

In "Simple" mode: queue waveforms and upload them all at once.

```python
c = Controller()

....

x = np.linspace(-1, 1, 200)
    y1 = x
    y2 = np.sinc(5 * x)

    n = 250  # MAX. ~250 waveforms.... otherwise sporadic disconnects and waveform corruption!
    for i in range(n):
        c.awg_queue_waveform(awg0, Waveform(i / n * y1, []))
        c.awg_queue_waveform(awg1, Waveform((1 - i / n) * y2, []))

    c.awg_upload_waveforms(awg0)
    c.awg_upload_waveforms(awg1)

```