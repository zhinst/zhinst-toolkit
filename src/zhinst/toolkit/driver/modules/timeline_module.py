"""Timeline Module."""

from __future__ import annotations

import logging
import typing as t

from zhinst.core import TimelineModule as ZITimelineModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class TimelineModule(BaseModule):
    """Timeline Module.

    The Timeline Module enables users to create pulsed or timed experiments,
    including waveform generation, triggering and data acquisition.


    Args:
        timeline_module: Instance of the core Timeline module.
        session: Session to the Data Server.
    """

    def __init__(self, timeline_module: ZITimelineModule, session: Session):
        super().__init__(timeline_module, session)

    def finish(self) -> None:
        """Stop the module."""
        self._raw_module.finish()

    def finished(self) -> bool:
        """Check if the timeline sequence has finished.

        Returns:
            True if the timeline sequence has finished.
        """
        return self._raw_module.finished()
