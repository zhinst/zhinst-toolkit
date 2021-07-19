# Copyright (C) 2021 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np

from zhinst.toolkit.interface import LoggerModule
from .shf_readout import SHFReadout

_logger = LoggerModule(__name__)


class SHFIntegration:
    """Implements an SHF Integration.

    This class represents the signal processing chain for one of the
    :class:`SHFIntegration` of the SHF device. Integration is typically
    used for dispersive resonator readout of superconducting qubits.

    """

    def __init__(self, parent: SHFReadout, index: int) -> None:
        self._parent = parent
        self._parent_index = self._parent._index
        self._index = index
        self._device = self._parent._parent._parent

    def _init_integration_params(self):
        """Initialize parameters associated with the integration unit.

        Can be overwritten by any Integration that inherits from the
        :class:`SHFIntegrationUnit`.

        """
        pass

    def _reset_int_weights(self):
        default_weights = np.zeros(4096, dtype=np.complex)
        self.weights(default_weights)

    def set_int_weights(self, weights):
        self._reset_int_weights()
        integration_length = self._parent.integration_length()
        if integration_length != len(weights):
            _logger.warning(
                f"The integration length is set to {integration_length} "
                f"but it does not match the length of the weights "
                f"vector. It will be automatically set to "
                f"{len(weights)}."
            )
            self._parent.integration_length(len(weights))
        self.weights(weights)

    @property
    def parent(self):
        return self._parent

    @property
    def device(self):
        return self._device

    @property
    def index(self):
        return self._index
