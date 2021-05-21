# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

from .shf_channel import SHFChannel
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
    """

    def __init__(self, parent: SHFChannel) -> None:
        self._parent = parent
        self._index = self._parent._index
        self._device = self._parent._parent
        self._module = ShfSweeper(
            daq=self._device._controller._connection._daq, dev=self._device.serial
        )
        self._channel_params = RfConfig
        self._trig_config = TriggerConfig
        self._sweep_params = SweepConfig
        self._avg_config = AvgConfig

    def _init_sweeper_params(self):
        """Initialize parameters associated with the sweeper.

        Can be overwritten by any Sweeper that inherits from the
        :class:`SHFSweeper`.

        """
        pass

    def run(self):
        """Perform a sweep with the specified settings.

        This method eventually wraps around the `run` method of
        `zhinst.utils.shf_sweeper`
        """
        self._update_channel_params()
        self._update_trigger_settings()
        self._update_sweep_params()
        self._update_averaging_settings()
        self._module.run()

    def get_result(self):
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

    def _update_channel_params(self):
        channel_params = self._channel_params(
            channel=self._index,
            input_range=int(self._parent.input_range()),
            output_range=int(self._parent.output_range()),
            center_freq=self._parent.center_freq(),
        )
        self._module.configure(rf_config=channel_params)

    def _update_trigger_settings(self):
        trig_config = self._trig_config(
            source=self._trigger_source,
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
            dwell_time=self.integration_time(),
            num_samples=self._num_averages,
            mode=self._averaging_mode,
        )
        self._module.configure(avg_config=avg_config)
