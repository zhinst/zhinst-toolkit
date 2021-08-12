# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .shf_qachannel import SHFQAChannel
from zhinst.utils.shf_sweeper import (
    ShfSweeper,
    RfConfig,
    TriggerConfig,
    SweepConfig,
    AvgConfig,
)


class SHFSweeper:
    """Implements a Sweeper representation for SHF devices.

    The :class:`SHFSweeper` class implements basic sweeper functionality
    of the SHF instrument.

    For example, the sweeper can be configured to run a spectroscopy
    measurement like this:

        >>> qachannel = shf.qachannels[0]
        >>> sweeper = qachannel.sweeper
        >>> # Set the mode to `spectroscopy`
        >>> qachannel.mode("spectroscopy")
        >>> # Set center frequency
        >>> qachannel.center_freq(8e9)
        >>> # Configure input
        >>> qachannel.input_range(0)
        >>> qachannel.input("on")
        >>> # Configure output
        >>> qachannel.output_range(0)
        >>> qachannel.output("on")
        >>> # Trigger settings
        >>> sweeper.trigger_source("channel0_trigger_input0")
        >>> sweeper.trigger_level(0)
        >>> sweeper.trigger_imp50(1)
        >>> # Sweep settings
        >>> sweeper.oscillator_gain(0.8)
        >>> sweeper.start_frequency(0)
        >>> sweeper.stop_frequency(200e6)
        >>> sweeper.num_points(51)
        >>> sweeper.mapping("linear")
        >>> # Averaging settings
        >>> sweeper.integration_time(100e-6)
        >>> sweeper.num_averages(2)
        >>> sweeper.averaging_mode("sequential")

    To run the measurement:

        >>> sweeper.run()
        Run a sweep with 51 frequency points in the range of [0.0, 200.0] MHz + 8.0 GHz.
        Mapping is linear.
        Dwell time = 0.0001 sec.
        Measures 2 times per frequency point.
        Averaging mode is sequential.
        Sweep at 200.00MHz.

    Obtain and plot the results:

        >>> result=sweeper.get_result()
        >>> sweeper.plot()

    Attributes:
        parent (:class:`SHFQAChannel`): The parent qachannel that this
            :class:`SHFSweeper` is associated to.
        device (:class:`BaseInstrument`): The instrument that this
            :class:`SHFSweeper` is associated to.
        index (int): An integer specifying the index in the instrument.
        name (str): The name of the `SHFSweeper`.

    """

    def __init__(self, parent: SHFQAChannel) -> None:
        self._parent = parent
        self._index = self._parent._index
        self._device = self._parent._parent
        self._module = ShfSweeper(
            daq=self._device._controller.connection.daq, dev=self._device.serial
        )
        self._qachannel_params = RfConfig
        self._trig_config = TriggerConfig
        self._sweep_params = SweepConfig
        self._avg_config = AvgConfig

    def _init_sweeper_params(self):
        """Initialize parameters associated with the sweeper.

        Can be overwritten by any Sweeper that inherits from the
        :class:`SHFSweeper`.

        """
        pass

    @property
    def parent(self):
        return self._parent

    @property
    def device(self):
        return self._device

    @property
    def index(self):
        return self._index

    @property
    def name(self):
        return self._device.name + "-" + "sweeper" + "-" + str(self._index)

    def run(self):
        """Perform a sweep with the specified settings.

        This method eventually wraps around the `run` method of
        `zhinst.utils.shf_sweeper`
        """
        self._update_qachannel_params()
        self._update_trigger_settings()
        self._update_sweep_params()
        self._update_averaging_settings()
        self._module.run()

    def read(self):
        """Get the measurement data of the last sweep.

        This method eventually wraps around the `get_result` method of
        `zhinst.utils.shf_sweeper`

        Returns:
             A dictionary with measurement data of the last sweep
             
        """
        return self._module.get_result()

    def plot(self):
        """Plot power over frequency for last sweep.

        This method eventually wraps around the `plot` method of
        `zhinst.utils.shf_sweeper`
        """
        return self._module.plot()

    def _update_qachannel_params(self):
        qachannel_params = self._qachannel_params(
            channel=self._index,
            input_range=int(self._parent.input_range()),
            output_range=int(self._parent.output_range()),
            center_freq=self._parent.center_freq(),
        )
        self._module.configure(rf_config=qachannel_params)

    def _update_trigger_settings(self):
        trig_config = self._trig_config(
            source=self.trigger_source(),
            level=self._trigger_level,
            imp50=self._trigger_imp50,
        )
        self._module.configure(trig_config=trig_config)

    def _update_sweep_params(self):
        sweep_params = self._sweep_params(
            start_freq=self._start_freq,
            stop_freq=self._stop_freq,
            num_points=self._num_points,
            mapping=self._mapping,
            oscillator_gain=self.oscillator_gain(),
        )
        self._module.configure(sweep_config=sweep_params)

    def _update_averaging_settings(self):
        avg_config = self._avg_config(
            integration_time=self.integration_time(),
            num_averages=self._num_averages,
            mode=self._averaging_mode,
        )
        self._module.configure(avg_config=avg_config)
