import pytest

from zhinst.toolkit.exceptions import ToolkitError


def test_base_exception():
    assert issubclass(ToolkitError, RuntimeError)


def test_base_exception_raises():
    with pytest.raises(RuntimeError):
        raise ToolkitError("message")
