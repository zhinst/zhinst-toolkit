# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import numpy as np
import time

from zhinst.toolkit.control.drivers.base import BaseInstrument
from zhinst.toolkit.interface import DeviceTypes, LoggerModule
from zhinst.toolkit.control.node_tree import Parameter
from zhinst.toolkit.control.parsers import Parse

_logger = LoggerModule(__name__)


class PQSC(BaseInstrument):
    """High-level driver for the Zurich Instruments PQSC.

        >>> import zhinst.toolkit as tk
        >>> pqsc = tk.PQSC("pqsc", "dev10000")
        >>> pqsc.setup()
        >>> pqsc.connect_device()
        >>> pqsc.nodetree
        >>> ...

    Arguments:
        name (str): Identifier for the PQSC.
        serial (str): Serial number of the device, e.g. 'dev1234'. The serial
            number can be found on the back panel of the instrument.
        discovery: an instance of ziDiscovery

    Attributes:
        ref_clock (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The intended reference clock source to be used as the
            frequency and time base reference. When the source is
            changed, all the instruments connected with ZSync links will
            be disconnected. The connection should be re-established
            manually. Can be either `0: "internal"` or `1: "external"`.\n
            `0: "internal"`: Internal 10 MHz clock\n
            `1: "external"`: An external clock. Provide a clean and stable
            10 MHz or 100 MHz reference to the appropriate back panel
            connector.
        ref_clock_actual (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The actual reference clock source. Can be either `0: "internal"`
            or `1: "external"`.\n
            `0: "internal"`: Internal 10 MHz clock\n
            `1: "external"`: An external clock.
        ref_clock_status (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            Status of the reference clock. Can be either `0: "locked"`,
            `1: "error"` or `2: "busy"`.
        progress (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The fraction of the triggers generated so far.
        repetitions (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The number of triggers sent over ZSync ports. Must be
            between 1 and 4.3M (default: 1).
        holdoff (:class:`zhinst.toolkit.control.node_tree.Parameter`):
            The time in seconds between repeated triggers sent over ZSync
            ports. Hold-off time has a minimum value and a granularity
            of 100 ns. Note that the PQSC is disabled at the end of the
            hold-off time after sending out the last trigger. Therefore,
            the hold-off time should be long enough such that the PQSC
            is still enabled when the feedback arrives. Otherwise, the
            feedback cannot be processed (default: 100e-9).

    """

    def __init__(self, name: str, serial: str, discovery=None, **kwargs) -> None:
        super().__init__(name, DeviceTypes.PQSC, serial, discovery, **kwargs)
        self.ref_clock = None
        self.ref_clock_actual = None
        self.ref_clock_status = None
        self.progress = None
        self._enable = None
        self.repetitions = None
        self.holdoff = None

    def connect_device(self, nodetree: bool = True) -> None:
        """Connects the device to the data server.

        Arguments:
            nodetree (bool): A flag that specifies if all the parameters from
                the device's nodetree should be added to the object's attributes
                as `zhinst-toolkit` Parameters. (default: True)

        """
        super().connect_device(nodetree=nodetree)

    def factory_reset(self, sync=True) -> None:
        """Load the factory default settings.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after loading the factory preset (default: True).
        """
        super().factory_reset(sync=sync)

    def arm(self, sync=True, repetitions: int = None, holdoff: float = None) -> None:
        """Prepare PQSC for triggering the instruments.

        This method configures the execution engine of the PQSC and
        clears the register bank. Optionally, the *number of triggers*
        and *hold-off time* can be set when specified as keyword
        arguments. If they are not specified, they are not changed.

        Note that the PQSC is disabled at the end of the hold-off time
        after sending out the last trigger. Therefore, the hold-off time
        should be long enough such that the PQSC is still enabled when
        the feedback arrives. Otherwise, the feedback cannot be processed.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after stopping the PQSC and clearing the
                register bank (default: True).
            repetitions (int): If specified, the number of triggers sent
                over ZSync ports will be set (default: None).
            holdoff (double): If specified, the time between repeated
                triggers sent over ZSync ports will be set. It has a
                minimum value and a granularity of 100 ns
                (default: None).

        """
        # Stop the PQSC if it is already running
        self.stop(sync=sync)
        if repetitions is not None:
            self.repetitions(repetitions)
        if holdoff is not None:
            self.holdoff(holdoff)
        # Clear register bank
        self._set("feedback/registerbank/reset", 1, sync=sync)

    def run(self, sync=True) -> None:
        """Start sending out triggers.

        This method activates the trigger generation to trigger all
        connected instruments over ZSync ports.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after enabling the PQSC (default: True).

        """
        self._enable(True, sync=sync)

    def arm_and_run(self, repetitions: int = None, holdoff: float = None) -> None:
        """Arm the PQSC and start sending out triggers.

        Simply combines the methods arm and run. A synchronisation
        is performed between the device and the data server after
        arming and running the PQSC.

        Arguments:
            repetitions (int): If specified, the number of triggers sent
                over ZSync ports will be set (default: None).
            holdoff (double): If specified, the time between repeated
                triggers sent over ZSync ports will be set. It has a
                minimum value and a granularity of 100 ns
                (default: None).

        """
        self.arm(sync=True, repetitions=repetitions, holdoff=holdoff)
        self.run(sync=True)

    def stop(self, sync=True) -> None:
        """Stop the trigger generation.

        Arguments:
            sync (bool): A flag that specifies if a synchronisation
                should be performed between the device and the data
                server after disabling the PQSC (default: True).
                
        """
        self._enable(False, sync=sync)

    def wait_done(self, timeout: float = 10, sleep_time: float = 0.005) -> None:
        """Wait until trigger generation and feedback processing is done.

        Arguments:
            timeout (float): The maximum waiting time in seconds for the
                PQSC (default: 10).
            sleep_time (float): Time in seconds to wait between
                requesting PQSC state

        Raises:
            TimeoutError: If the PQSC is not done sending out all
                triggers and processing feedback before the timeout.

        """
        start_time = time.time()
        while self.is_running and start_time + timeout >= time.time():
            time.sleep(sleep_time)
        if self.is_running and start_time + timeout < time.time():
            _logger.error(
                "PQSC timed out!",
                _logger.ExceptionTypes.TimeoutError,
            )

    def check_ref_clock(
        self, blocking: bool = True, timeout: int = 30, sleep_time: int = 1
    ) -> None:
        """Check if reference clock is locked successfully.

        Keyword Arguments:
            blocking (bool): A flag that specifies if the program should
                be blocked until the reference clock is 'locked'.
                (default: True)
            timeout (int): Maximum time in seconds the program waits
                when `blocking` is set to `True` (default: 30).
            sleep_time (int): Time in seconds to wait between
                requesting the reference clock status (default: 1)

        Raises:
            ToolkitError: If the device fails to lock on the reference
                clock.

        """
        self._check_ref_clock(blocking=blocking, timeout=timeout, sleep_time=sleep_time)

    def check_zsync_connection(self, ports=0, blocking=True, timeout=30) -> None:
        """Check if the ZSync connection on the given port is successful.

        This function checks the current status of the instrument
        connected to the given port.

        Arguments:
            ports (list) or (int): The port numbers to check the ZSync
                connection for. It can either be a single port number given
                as integer or a list of several port numbers. (default: 0)
            blocking (bool): A flag that specifies if the program should
                be blocked until the status is 'connected'.
                (default: False)
            timeout (int): Maximum time in seconds the program waits
                when `blocking` is set to `True`. (default: 30)

        Raises:
            ToolkitError: If ZSync connection to the instruments on the
                specified ports is not established.

        """
        if type(ports) is not list:
            ports = [ports]
        for port in ports:
            zsync_connection_status = self._get(f"zsyncs/{port}/connection/status")
            start_time = time.time()
            while (
                blocking
                and start_time + timeout >= time.time()
                and zsync_connection_status != 2
            ):
                time.sleep(1)
                # Check again if status is 'connected' and update the variable.
                zsync_connection_status = self._get(f"zsyncs/{port}/connection/status")
            # Throw an exception if the instrument is still not connected after timeout
            if zsync_connection_status != 2:
                _logger.error(
                    f"Check ZSync connection to the instrument on port {port} "
                    f"(port {port + 1} on the rear panel) of PQSC.",
                    _logger.ExceptionTypes.ToolkitError,
                )
            else:
                _logger.info(
                    f"ZSync connection to the instrument on port {port} "
                    f"(port {port + 1} on the rear panel) of PQSC is successful"
                )

    def _init_settings(self):
        """Sets initial device settings on startup."""
        pass

    def _init_params(self):
        """Initialize parameters associated with device nodes."""
        super()._init_params()
        self.ref_clock = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/source"),
            device=self,
            auto_mapping=True,
        )
        self.ref_clock_actual = Parameter(
            self,
            self._get_node_dict(f"system/clocks/referenceclock/in/sourceactual"),
            device=self,
            auto_mapping=True,
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
        self._enable = Parameter(
            self,
            self._get_node_dict(f"execution/enable"),
            device=self,
            set_parser=Parse.set_true_false,
            get_parser=Parse.get_true_false,
        )
        self.repetitions = Parameter(
            self,
            self._get_node_dict(f"execution/repetitions"),
            device=self,
            set_parser=[
                lambda v: Parse.greater_equal(v, 1),
                lambda v: Parse.smaller_equal(v, 2 ** 32 - 1),
            ],
        )
        self.holdoff = Parameter(
            self,
            self._get_node_dict(f"execution/holdoff"),
            device=self,
            set_parser=[
                lambda v: Parse.greater_equal(v, 100e-9),
                lambda v: Parse.multiple_of(v, 100e-9, "nearest"),
            ],
        )

    @property
    def is_running(self):
        return self._enable()
