import numpy as np
import time
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


def voltage_to_power_dBm(voltage):
    power = 10 * np.log10(np.abs(voltage) ** 2 / 50 * 1000)
    return power


def voltage_to_phase(voltage):
    phase = np.unwrap(np.angle(voltage))
    return phase


def generate_flat_top_gaussian(
    frequencies, pulse_duration, rise_fall_time, sampling_rate, scaling=0.9
):
    """Returns complex flat top Gaussian waveforms modulated with the given frequencies.

    Args:

        frequencies (array): array specifying the modulation frequencies applied to each
                             output wave Gaussian

        pulse_duration (float): total duration of each Gaussian in seconds

        rise_fall_time (float): rise-fall time of each Gaussian edge in seconds

        sampling_rate (float): sampling rate in samples per second based on which to
                               generate the waveforms

        scaling (optional float): scaling factor applied to the generated waveforms (<=1);
                                  use a scaling factor <= 0.9 to avoid overshoots

    Returns:

        pulses (dict): dictionary containing the flat top Gaussians as values

    """
    if scaling > 1:
        raise ValueError(
            "The scaling factor has to be <= 1 to ensure the generated waveforms lie within the \
                unit circle."
        )

    from scipy.signal import gaussian

    rise_fall_len = int(rise_fall_time * sampling_rate)
    pulse_len = int(pulse_duration * sampling_rate)

    std_dev = rise_fall_len // 10

    gauss = gaussian(2 * rise_fall_len, std_dev)
    flat_top_gaussian = np.ones(pulse_len)
    flat_top_gaussian[0:rise_fall_len] = gauss[0:rise_fall_len]
    flat_top_gaussian[-rise_fall_len:] = gauss[-rise_fall_len:]

    flat_top_gaussian *= scaling

    pulses = {}
    time_vec = np.linspace(0, pulse_duration, pulse_len)

    for i, f in enumerate(frequencies):
        pulses[i] = flat_top_gaussian * np.exp(2j * np.pi * f * time_vec)

    return pulses


def set_trigger_loopback(session, device, rate=1000):
    """
    Start a continuous trigger pulse from marker 1 A using the internal loopback to trigger in 1 A
    """

    m_ch = 0
    low_trig = 2
    continuous_trig = 1
    daq = session.daq_server
    daq.syncSetInt(f"/{device.serial}/raw/markers/*/testsource", low_trig)
    daq.setInt(f"/{device.serial}/raw/markers/{m_ch}/testsource", continuous_trig)
    daq.setDouble(f"/{device.serial}/raw/markers/{m_ch}/frequency", rate)
    daq.setInt(f"/{device.serial}/raw/triggers/{m_ch}/loopback", 1)
    time.sleep(0.2)


def clear_trigger_loopback(session, device):
    m_ch = 0
    session.daq_server.setInt(f"/{device.serial}/raw/markers/*/testsource", 0)
    session.daq_server.setInt(f"/{device.serial}/raw/triggers/{m_ch}/loopback", 0)


def run_experiment(device, sgchannel_number, number_of_qubits, reenable=False):
    if reenable:
        with device.set_transaction():
            device.qachannels[0].readout.run()
            device.qachannels[0].generator.enable_sequencer(single=True)
            device.qachannels[0].input.on(1)
            device.qachannels[0].output.on(1)
            for qubit in range(number_of_qubits):
                channel = sgchannel_number[qubit]
                device.sgchannels[channel].awg.enable(1)
                device.sgchannels[channel].output.on(1)
    else:
        with device.set_transaction():
            device.qachannels[0].input.on(1)
            device.qachannels[0].output.on(1)
            for qubit in range(number_of_qubits):
                device.sgchannels[sgchannel_number[qubit]].output.on(1)

    device.start_continuous_sw_trigger(num_triggers=1, wait_time=2e-3)

    readout_results = device.qachannels[0].readout.read(timeout=100)

    with device.set_transaction():
        device.qachannels[0].input.on(0)
        device.qachannels[0].output.on(0)
        for qubit in range(number_of_qubits):
            device.sgchannels[sgchannel_number[qubit]].output.on(0)

    return readout_results


def fit_data(
    x_data,
    y_data,
    function,
    start_param,
    do_plot,
    figsize=10,
    font=10,
    qubit=0,
    x_label="",
    y_label="",
    saveloc="",
):

    pars, cov = curve_fit(
        f=function, xdata=x_data, ydata=y_data, p0=start_param, bounds=(-np.inf, np.inf)
    )
    stdevs = np.sqrt(np.diag(cov))
    residuals = y_data - function(x_data, *pars)

    # plot it
    if do_plot:
        fig4, axs = plt.subplots(2, 1, figsize=figsize)
        fig4.suptitle(f"Qubit {qubit}", fontsize=font)
        axs[0].scatter(x_data, y_data, s=20, color="#00b3b3", label="Data")
        axs[0].plot(
            x_data, function(x_data, *pars), linestyle="--", linewidth=2, color="black"
        )
        axs[0].legend(loc=2, prop={"size": font})

        axs[0].set_xlabel(x_label, fontsize=font)
        axs[0].set_ylabel(y_label, fontsize=font)
        axs[0].tick_params(axis="both", which="major", labelsize=font)

        axs[1].plot(x_data, residuals, ".")
        axs[1].set_xlabel(x_label, fontsize=font)
        axs[1].set_ylabel("residuals", fontsize=font)
        axs[1].tick_params(axis="both", which="major", labelsize=font)

        plt.savefig(saveloc)
        plt.show()

    return pars, stdevs


def amplitude_rabi(amp, Omega, amplitude):
    return -amplitude * np.cos(amp * Omega / 2) + amplitude
