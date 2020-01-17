# ZI_driver_wrapper

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
