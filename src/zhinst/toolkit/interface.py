"""Interface Enums for the zhinst.toolkit."""
from enum import Enum, IntEnum


class SHFQAChannelMode(Enum):
    """SHFQA channel mode."""

    SPECTROSCOPY = "spectroscopy"
    READOUT = "readout"


class AveragingMode(IntEnum):
    """Averaging modes.

    CYCLIC:
        All frequency points are measured once from start frequency to stop
        frequency. The sweeper then moves back to start frequency and repeats the
        sweep the number of times specified by the number of averages setting.

    SEQUENTIAL:
        A frequency point is measured the number of times specified by the
        number of averages setting. In other words, the same frequency point is
        measured repeatedly until the number of averages is reached and the
        sweeper then moves to the next frequency point.
    """

    CYCLIC = 0
    SEQUENTIAL = 1
