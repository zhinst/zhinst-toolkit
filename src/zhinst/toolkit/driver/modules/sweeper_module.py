"""Sweeper Module."""

import logging
import typing as t

from zhinst.core import SweeperModule as ZISweeperModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class SweeperModule(BaseModule):
    """Implements a base Sweeper Module for Lock-In instruments.

    The Sweeper Module allows for simple and efficient parameter sweeps while
    acquiring data streams from multiple different signal sources. The module
    supports well defined sweeps of various parameters as well as application
    specific measurement presets. For more information on how to use the Sweeper
    Module, have a look at the LabOne Programming Manual.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_programming_manual/sweeper_module.html

    Args:
        sweeper_module: Instance of the core Sweeper Module.
        session: Session to the Data Server.
    """

    def __init__(self, sweeper_module: ZISweeperModule, session: "Session"):
        super().__init__(sweeper_module, session)
        self.root.update_nodes(
            {
                "/gridnode": {
                    "GetParser": self._get_node,
                    "SetParser": self._set_node,
                }
            },
            raise_for_invalid_node=False,
        )

    def finish(self) -> None:
        """Stop the module.

        .. versionadded:: 0.5.0
        """
        self._raw_module.finish()
