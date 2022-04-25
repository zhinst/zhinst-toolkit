"""SHFQA Instrument Driver."""

import logging

from zhinst.toolkit.driver.devices import SHFQA, SHFSG

logger = logging.getLogger(__name__)


class SHFQC(SHFQA, SHFSG):
    """High-level driver for the Zurich Instruments SHFQC."""
