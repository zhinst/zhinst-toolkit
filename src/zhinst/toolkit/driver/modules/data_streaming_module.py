"""Data Streaming Module."""

from __future__ import annotations

import logging
import typing as t

from zhinst.core import DataStreamingModule as ZIDataStreamingModule

from zhinst.toolkit.driver.modules.base_module import BaseModule

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class DataStreamingModule(BaseModule):
    """Data Streaming Module.

    The Data Streaming Module provides functionality for continuous streaming of signals
    to the the API client and saving of data to file.
    The streamed signals are resampled onto a common sampling grid corresponding to that
    with the highest sampling rate. Linear interpolation is used for upsampling.
    The module provides a minimal interface - the duration of the capture is all that has
    to be specified, plus some extra parameters if saving to file is required.



    Args:
        data_streaming_module: Instance of the core DAQ module.
        session: Session to the Data Server.
    """

    def __init__(self, data_streaming_module: ZIDataStreamingModule, session: Session):
        super().__init__(data_streaming_module, session)

    def finish(self) -> None:
        """Stop the module."""
        self._raw_module.finish()

    def finished(self) -> bool:
        """Check if the acquisition has finished.

        Returns:
            Flag if the acquisition has finished.
        """
        return self._raw_module.finished()
