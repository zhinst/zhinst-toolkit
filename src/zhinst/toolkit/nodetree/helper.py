"""Helper functions used in toolkit."""
import typing as t
from contextlib import contextmanager
from collections.abc import Mapping
import re
from _thread import RLock  # type: ignore
from functools import wraps

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

_NOT_FOUND = object()


# Exact implementation of functools.cached_property from Python 3.8
# This is needed for Python 3.7 compatibility
# It should be removed once we drop support for Python 3.7
class lazy_property:
    """Copied functools.cached_property from Python 3.8.

    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    """

    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner, name):
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self.attrname!r} and {name!r})."
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without "
                "calling __set_name__ on it."
            )
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = (
                            f"The '__dict__' attribute on {type(instance).__name__!r} "
                            "instance does not support item assignment for caching "
                            f"{self.attrname!r} property."
                        )
                        raise TypeError(msg) from None
        return val


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


def resolve_wildcards_labone(path: str, nodes: t.List[str]) -> t.List[str]:
    """Resolves potential wildcards.

    Also will resolve partial nodes to its leaf nodes.

    Returns:
        List of matched nodes in the raw path format
    """
    node_raw = re.escape(path)
    node_raw = node_raw.replace("/\\*/", "/[^/]*/").replace("/\\*", "/*") + "(/.*)?$"
    node_raw_regex = re.compile(node_raw)
    return list(filter(node_raw_regex.match, nodes))


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


def not_callable_in_transactions(
    func: t.Callable[["Node", t.Any], t.Any]
) -> t.Callable[["Node", t.Any], t.Any]:
    """Wrapper to prevent certain functions from being used within a transaction.

    Certain utils functions which that both get and set values would not work like
    expected in a transaction. This wrapper prevents misuse by throwing an error
    in such cases.

    Args:
        func: function to wrap

    Returns:
        Similar function, but not callable from transactions
    """

    @wraps(func)
    def wrapper(node: "Node", *args, **kwargs):
        if node.root.transaction.in_progress():
            raise RuntimeError(
                f"'{func.__name__}' cannot be called inside a transaction"
            )
        return func(node, *args, **kwargs)

    return wrapper
