"""Scope Module."""

import logging
import typing as t

from zhinst.core import ScopeModule as ZIScopeModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class ScopeModule(BaseModule):
    """Scope Module.

    The Scope Module corresponds to the functionality available in the Scope
    tab in the LabOne User Interface and provides API users with an interface
    to acquire assembled and scaled scope data from the instrument
    programmatically.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_programming_manual/scope_module.html


    Although it is possible to acquire scope data using the lower-level
    subscribe/poll method, the Scope Module provides API users with several
    advantages. Specifically, the Scope Module:

    * Provides a uniform interface to acquire scope data from all instrument
      classes (HF2 scope usage differs from and MF and UHF devices, especially
      with regards to scaling).
    * Scales and offsets the scope wave data to get physically meaningful
      values. If data is polled from the device node using subscribe/poll the
      scaling and offset must be applied manually.
    * Assembles large multi-block transferred scope data into single complete
      records. When the scope is configured to record large scope lengths and
      data is directly polled from the device node /DEV…​/SCOPES/n/WAVE the data
      is split into multiple blocks for efficient transfer of data from the
      Data Server to the API; these must then be programmatically reassembled.
      The Scope Module performs this assembly and returns complete scope
      records (unless used in pass-through mode, mode=0).
    * Can be configured to return the FFT of the acquired scope records
      (with mode=3) as provided by the Scope Tab in the LabOne UI. FFT data is
      not available from the device nodes in the /DEV/…​./SCOPES/ branch using
      subscribe/poll.
    * Can be configured to average the acquired scope records the
      averager/parameters.
    * Can be configured to return a specific number of scope records using the
      historylength parameter.

    Args:
        scope_module: Instance of the core scope module.
        session: Session to the Data Server.

    .. versionadded:: 0.5.0
    """

    def __init__(self, scope_module: ZIScopeModule, session: "Session"):
        super().__init__(scope_module, session)

    def finish(self) -> None:
        """Stop the module."""
        self._raw_module.finish()
