# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""SHFQA Instrument Driver."""

import logging

from zhinst.toolkit.driver.devices import SHFQA, SHFSG

logger = logging.getLogger(__name__)


class SHFQC(SHFQA, SHFSG):
    """High-level driver for the Zurich Instruments SHFQC."""
