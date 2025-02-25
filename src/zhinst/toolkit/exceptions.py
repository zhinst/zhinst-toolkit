"""Global zhinst-toolkit exceptions."""


class ToolkitError(RuntimeError):
    """Base class for `zhinst.toolkit` errors."""


class ValidationError(ToolkitError):
    """Data validation failed."""
