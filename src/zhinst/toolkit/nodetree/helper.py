"""Helper functions used in toolkit"""
import typing as t
from contextlib import contextmanager
from functools import lru_cache

T = t.TypeVar("T")


def lazy_property(property_function: t.Callable[..., T]) -> T:
    """Alternative for functools.lazy_property.

    functools.lazy_property is only available since python 3.8.
    Should be replaced with functools.lazy_property once no version below
    python 3.8 is supported.

    Args:
        property_function (Callable): property function

    Returns
        Any: Retun value of the property function

    """
    return property(lru_cache()(property_function))


@contextmanager
def create_or_append_set_transaction(nodetree) -> None:
    """Context manager for a transactional set.

    In contrast to the set_transaction from the nodetree this function only
    creates a new transaction if no other is in progress.
    Should only be called withing the toolkit code.

    Warning:
        This function will silently fail if the existing transaction is exited
        before this function finishes.

    Warning:
        The set is always perfromed as deep set if called on device nodes.

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
