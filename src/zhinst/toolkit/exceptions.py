# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.
"""Global zhinst-toolkit exceptions."""


class ToolkitError(RuntimeError):
    """Base class for `zhinst.toolkit` errors."""


class ValidationError(ToolkitError):
    """Data validation failed."""
