"""Global zhinst-toolkit exceptions."""


class ToolkitError(RuntimeError):
    """Base class for `zhinst.toolkit` errors.

    .. versionadded:: 0.5.1
    """


class ValidationError(ToolkitError):
    """Data validation failed.

    .. versionchanged:: 0.5.1

         Changed base class from `Exception` to `ToolkitError`.
    """
