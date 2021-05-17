# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time
import logging

from zhinst.toolkit.control.drivers.base import BaseInstrument
from zhinst.toolkit.interface import DeviceTypes
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse

_logger = logging.getLogger(__name__)


class PQSC(BaseInstrument):
    """High-level driver for the Zurich Instruments PQSC.

        >>> import zhinst.toolkit as tk
        >>> pqsc = tk.PQSC("pqsc", "dev1234")
        >>> pqsc.setup()
        >>> pqsc.connect_device()
        >>> pqsc.nodetree
        >>> ...

    Arguments:
        name (str): Identifier for the PQSC.
        serial (str): Serial number of the device, e.g. 'dev1234'. The serial
            number can be found on the back panel of the instrument.
        discovery: an instance of ziDiscovery
    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.PQSC, serial, discovery, **kwargs)
        self.ref_clock = None
        self.ref_clock_actual = None
        self.ref_clock_status = None
        self.progress = None

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server.

        Keyword Arguments:
            nodetree (bool): A flag that specifies if all the parameters from
                the device's nodetree should be added to the object's attributes
                as `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)

    def factory_reset(self) -> None:
        """Loads the factory default settings."""
        super().factory_reset()

    def arm(self, repetitions=None, holdoff=None) -> None:
        """Prepare PQSC for triggering the instruments.

        This method configures the execution engine of the PQSC and
        clears the register bank. Optionally, the *number of triggers*
        and *hold-off time* can be set when specified as keyword
        arguments. If they are not specified, they are not changed.

        Note that the PQSC is disabled at the end of the hold-off time
        after sending out the last trigger. Therefore, the hold-off time
        should be long enought such that the PQSC is still enabled when
        the feedback arrives. Otherwise, the feedback cannot be processed.

        Keyword Arguments:
            repetitions (int): If specified, the number of triggers sent
                over ZSync ports will be set. (default: None)
            holdoff (double): If specified, the time between repeated
                triggers sent over ZSync ports will be set. It has a
                minimum value and a granularity of 100 ns. (default: None)

        """
        # Stop the PQSC if it is already running
        self._set("execution/enable", 0)
        if repetitions is not None:
            self._set("execution/repetitions", int(repetitions))
        if holdoff is not None:
            if holdoff < 100e-9:
                raise ValueError("Hold-off time cannot be smaller than 100 ns!")
            elif holdoff % 100e-9 > 1e-10:
                raise ValueError("Hold-off time must be multiples of 100 ns!")
            else:
                self._set("execution/holdoff", holdoff)
        # Clear register bank
        self._set("feedback/registerbank/reset", 1)

    def run(self) -> None:
        """Start sending triggers.

        This method activates the trigger generation to trigger all
        connected instruments over ZSync ports.
        """
        self._set("execution/enable", 1)

    def stop(self) -> None:
        """Stops the trigger generation."""
        self._set("execution/enable", 0)

    def check_ref_clock(self, blocking=True, timeout=30) -> None:
        """Check if reference clock is locked succesfully.

        Keyword Arguments:
            blocking (bool): A flag that specifies if the program should
                be blocked until the reference clock is 'locked'.
                (default: False)
            timeout (int): Maximum time in seconds the program waits
                when `blocking` is set to `True`. (default: 5)

        """
        ref_clock_set = self._get("system/clocks/referenceclock/in/source")
        ref_clock_status = self._get("system/clocks/referenceclock/in/status")
        start_time = time.time()
        while (
            blocking and start_time + timeout >= time.time() and ref_clock_status != 0
        ):
            time.sleep(1)
            # Check again if status is 'locked' and update the variable.
            ref_clock_status = self._get("system/clocks/referenceclock/in/status")
        # Throw an exception if the clock is still not locked after timeout
        ref_clock_actual = self._get("system/clocks/referenceclock/in/sourceactual")
        if ref_clock_actual != ref_clock_set:
            raise Exception(
                "There was an error locking PQSC onto reference clock signal. Try again."
            )
        else:
            _logger.info("Reference clock has been succesfully locked on.")

    def _init_settings(self):
        """Sets initial device settings on startup."""
        pass

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        self.ref_clock = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/source"),
            device=self,
            set_parser=Parse.set_ref_clock_wo_zsync,
            get_parser=Parse.get_ref_clock_wo_zsync,
        )
        self.ref_clock_actual = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/sourceactual"),
            device=self,
            get_parser=Parse.get_ref_clock_wo_zsync,
        )
        self.ref_clock_status = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/status"),
            device=self,
            get_parser=Parse.get_locked_status,
        )
        self.progress = Parameter(
            self,
            self._get_node_dict(f"execution/progress"),
            device=self,
        )
