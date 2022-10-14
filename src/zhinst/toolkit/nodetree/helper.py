"""Helper functions used in toolkit."""
import typing as t
from contextlib import contextmanager
from functools import lru_cache
from collections.abc import Mapping

# TypedDict is available in the typing module since 3.8
# Ift we only support 3.8 we should switch to t.TypedDict
from typing_extensions import TypedDict

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.nodetree.node import Node

T = t.TypeVar("T")

_NodeInfo = TypedDict(
    "_NodeInfo",
    {
        "Node": str,
        "Description": str,
        "Properties": str,
        "Type": str,
        "Unit": str,
        "Options": t.Dict[str, str],
    },
)
NodeDoc = t.Dict[str, _NodeInfo]


def lazy_property(property_function: t.Callable[..., T]) -> property:
    """Alternative for functools.lazy_property.

    functools.lazy_property is only available since python 3.8.
    Should be replaced with functools.lazy_property once no version below
    python 3.8 is supported.

    Args:
        property_function (Callable): property function

    Returns
        Return value of the property function

    """
    return property(lru_cache()(property_function))


@contextmanager
def create_or_append_set_transaction(nodetree) -> t.Generator[None, None, None]:
    """Context manager for a transactional set.

    In contrast to the set_transaction from the nodetree this function only
    creates a new transaction if no other is in progress.
    Should only be called withing the toolkit code.

    Warning:
        This function will silently fail if the existing transaction is exited
        before this function finishes.

    Warning:
        The set is always performed as deep set if called on device nodes.

    Examples:
        >>> with nodetree.set_transaction():
                nodetree.test[0].a(1)
                with create_or_append_set_transaction(nodetree):
                    nodetree.test[1].a(2)
                nodetree.test[2].a(2)
    """
    if not nodetree.transaction.in_progress():
        with nodetree.set_transaction():
            yield
    else:
        yield


class NodeDict(Mapping):
    """Mapping of dictionary structure results.

    The mapping allows to access data with both the string and the toolkit
    node objects.

    Args:
        result: A dictionary of node/value pairs.

    Example:
        >>> result = device.demods["*"].enable()
        >>> print(result)
        {
            '/dev1234/demods/0/enable': 0,
            '/dev1234/demods/1/enable': 1,
        }
        >>> result[device.demods[0].enable]
        0
        >>> result["/dev1234/demods/0/enable"]
        0

    .. versionadded:: 0.3.5 Renamed from WildcardResult
    """

    def __init__(self, result: t.Dict[str, t.Any]):
        self._result = result

    def __repr__(self):
        return repr(self._result)

    def __getitem__(self, key: t.Union[str, "Node"]):
        return self._result[str(key)]

    def __iter__(self):
        return iter(self._result)

    def __len__(self):
        return len(self._result)

    def to_dict(self) -> t.Dict[str, t.Any]:
        """Convert the WildcardResult to a dictionary.

        After conversion, :class:`Node` objects cannot be used to get items.
        """
        return self._result
