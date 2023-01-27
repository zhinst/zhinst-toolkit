"""Global zhinst-toolkit exceptions."""


class ToolkitError(RuntimeError):
    """Base class for `zhinst.toolkit` errors.

    .. versionadded:: 0.5.2
    """


class ValidationError(ToolkitError):
    """Data validation failed.

    .. versionchanged:: 0.5.2

         Changed base class from `Exception` to `ToolkitError`.
    """
