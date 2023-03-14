"""Predefined parsers for device specific nodes."""
import logging

UHFQA_SAMPLE_RATE = 1.8e9
SHFQA_SAMPLE_RATE = 2e9
logger = logging.getLogger(__name__)


class Parse:
    """Input and output parsers for node parameters to validate and parse values."""

    @staticmethod
    def from_bool(value: bool) -> int:
        """Convert a boolean value to a integer value.

        Args:
            value: A boolean value.

        Returns:
            Integer value.
        """
        return int(value)

    @staticmethod
    def to_bool(value: int) -> bool:
        """Convert a integer value to a boolean value.

        Args:
            value: A integer value.

        Returns:
            Boolean value.
        """
        return bool(value)

    @staticmethod
    def phase(raw_phase: float) -> float:
        """Corrects the phase to -180 <= value <= 180.

        Args:
            raw_phase: Raw input phase.

        Returns:
            Corrected phase.
        """
        return (raw_phase + 180) % 360 - 180

    @staticmethod
    def greater_equal(value: float, limit: float) -> float:
        """Ensures that the value is greater or equal a lower limit.

        Args:
            value: Used value.
            limit: Minimum value returned.

        Returns:
            Clamped value.
        """
        if value < limit:
            logger.warning(
                f"The value {value:.3e} must be greater than or equal to "
                f"{limit:.3e} and will be rounded up to: "
                f"{limit:.3e}"
            )
            return limit
        else:
            return value

    @staticmethod
    def smaller_equal(value: float, limit: float) -> float:
        """Ensures that the value is smaller or equal a upper limit.

        Args:
            value: Used value.
            limit: Maximum value returned.

        Returns:
            Clamped value.
        """
        if value > limit:
            logger.warning(
                f"The value {value:.3e} must be smaller than or equal to "
                f"{limit:.3e} and will be rounded down to: "
                f"{limit:.3e}",
            )
            return limit
        else:
            return value

    @staticmethod
    def multiple_of(value: float, factor: float, rounding: str) -> float:
        """Rounds a value to a multiple of a given factor.

        Args:
            value: Input value.
            factor: Factor that the value needs to be multiple of.
            rounding: Method of rounding (nearest, down).

        Returns:
            Rounded value.

        .. versionchanged:: 0.5.3

            Invalid `rounding` value raises `ValueError` instead of `RuntimeError`.
        """
        if abs(round(value / factor) * factor - value) < 1e-12:
            return value
        elif rounding == "nearest":
            v_rounded = round(value / factor) * factor
            logger.warning(
                f"The value {value:.3e} is not a multiple of "
                f"{factor:.3e} and will be rounded to nearest "
                f"multiple: {v_rounded:.3e}",
            )
            return v_rounded
        elif rounding == "down":
            v_rounded = round(value // factor) * factor
            logger.warning(
                f"The value {value:.3e} is not a multiple of "
                f"{factor:.3e} and will be rounded down to greatest "
                f"multiple: {v_rounded:.3e}",
            )
            return v_rounded
        raise ValueError(
            f"Invalid rounding type {rounding} only the "
            "following values are allowed: [nearest,down]"
        )


node_parser = {
    "SHFQA": {
        "scopes/0/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "scopes/0/channels/*/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "scopes/0/trigger/delay": {
            "SetParser": lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        },
        "scopes/0/length": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 16),
                lambda v: Parse.smaller_equal(v, 2**18),
                lambda v: Parse.multiple_of(v, 16, "down"),
            ],
        },
        "scopes/0/segments/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "scopes/0/segments/count": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "scopes/0/averaging/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "scopes/0/averaging/count": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "qachannels/*/input/on": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "qachannels/*/output/on": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "qachannels/*/input/range": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, -50),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        },
        "qachannels/*/output/range": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, -50),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        },
        "qachannels/*/centerfreq": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 1e9),
                lambda v: Parse.smaller_equal(v, 8e9),
                lambda v: Parse.multiple_of(v, 100e6, "nearest"),
            ],
        },
        "qachannels/*/generator/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "qachannels/*/generator/delay": {
            "SetParser": lambda v: Parse.multiple_of(v, 2e-9, "nearest"),
        },
        "qachannels/*/generator/single": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "qachannels/*/readout/result/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "qachannels/*/oscs/0/gain": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, 0.0),
            ],
        },
        "qachannels/*/spectroscopy/length": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 4),
                lambda v: Parse.smaller_equal(v, ((2**23) - 1) * 4),
                lambda v: Parse.multiple_of(v, 4, "down"),
            ],
        },
        "qachannels/*/spectroscopy/delay": {
            "SetParser": lambda v: Parse.multiple_of(v, 2e-9, "nearest")
        },
    },
    "SHFSG": {
        "system/clocks/referenceclock/out/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "system/clocks/referenceclock/out/freq": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "sgchannels/*/centerfreq": {
            "SetParser": lambda v: Parse.greater_equal(v, 0),
        },
        "sgchannels/*/output/on": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "sgchannels/*/output/range": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, -30),
                lambda v: Parse.smaller_equal(v, 10),
                lambda v: Parse.multiple_of(v, 5, "nearest"),
            ],
        },
        "sgchannels/*/awg/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "sgchannels/*/awg/single": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "sgchannels/*/awg/outputs/*/enables/*": {
            "GetParser": Parse.to_bool,
        },
        "sgchannels/*/awg/outputs/*/gains/*": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 1.0),
                lambda v: Parse.greater_equal(v, -1.0),
            ],
        },
        "sgchannels/*/oscs/*/freq": {
            "SetParser": [
                lambda v: Parse.smaller_equal(v, 1e9),
                lambda v: Parse.greater_equal(v, -1e9),
            ],
        },
        "sgchannels/*/sines/*/phaseshift": {
            "SetParser": Parse.phase,
        },
        "sgchannels/*/sines/*/oscselect": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 0),
                lambda v: Parse.smaller_equal(v, 7),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        },
        "sgchannels/*/sines/*/harmonic": {
            "SetParser": [
                lambda v: Parse.greater_equal(v, 1),
                lambda v: Parse.smaller_equal(v, 1023),
                lambda v: Parse.multiple_of(v, 1, "nearest"),
            ],
        },
        "sgchannels/*/sines/*/i/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
        "sgchannels/*/sines/*/q/enable": {
            "GetParser": Parse.to_bool,
            "SetParser": Parse.from_bool,
        },
    },
}
