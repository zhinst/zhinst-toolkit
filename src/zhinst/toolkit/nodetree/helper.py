"""Helper functions used in toolkit."""

import re
import typing as t
from collections.abc import Mapping
from contextlib import contextmanager
from functools import wraps

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.nodetree.node import Node

T = t.TypeVar("T")


class _NodeInfo(t.TypedDict):
    Node: str
    Description: str
    Properties: str
    Type: str
    Unit: str
    Options: dict[str, str]


NodeDoc = dict[str, _NodeInfo]


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

    Example:
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


def resolve_wildcards_labone(path: str, nodes: list[str]) -> list[str]:
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
    """

    def __init__(self, result: dict[str, t.Any]):
        self._result = result

    def __repr__(self):
        return repr(self._result)

    def __getitem__(self, key: t.Union[str, "Node"]):
        return self._result[str(key)]

    def __iter__(self):
        return iter(self._result)

    def __len__(self):
        return len(self._result)

    def to_dict(self) -> dict[str, t.Any]:
        """Convert the WildcardResult to a dictionary.

        After conversion, `Node` objects cannot be used to get items.
        """
        return self._result


def not_callable_in_transactions(
    func: t.Callable[["Node", t.Any], t.Any],
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
            msg = f"'{func.__name__}' cannot be called inside a transaction"
            raise RuntimeError(
                msg,
            )
        return func(node, *args, **kwargs)

    return wrapper
