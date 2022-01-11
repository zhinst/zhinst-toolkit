"""High-level generic lazy node tree for the ziPython package."""

import fnmatch
import json
import typing as t
from keyword import iskeyword as is_keyword

try:
    # Protocol is available in the typing module since 3.8
    Protocol = t.Protocol
except AttributeError:
    from typing_extensions import Protocol

from contextlib import contextmanager

from zhinst.toolkit.nodetree.node import Node


class Connection(Protocol):
    """Protocol class for the connection used in the nodetree.

    Every connection object used in the Nodetree is expected to have at least
    this interface in order to work with the Nodetree.
    """

    # pylint: disable=invalid-name
    def listNodesJSON(self, path: str, *args, **kwargs) -> str:
        """Returns a list of nodes with description found at the specified path."""

    def get(self, path: str, *args, **kwargs) -> object:
        """Mirrors the behaviour of ziPython ``get`` command."""

    def getInt(self, path: str) -> int:
        """Mirrors the behaviour of ziPython ``getInt`` command."""

    def getDouble(self, path: str) -> float:
        """Mirrors the behaviour of ziPython ``getDouble`` command."""

    def getString(self, path: str) -> str:
        """Mirrors the behaviour of ziPython ``getDouble`` command."""

    def set(self, path: str, value: object, **kwargs) -> None:
        """Mirrors the behaviour of ziPython ``set`` command."""

    def subscribe(self, path: str) -> None:
        """Mirrors the behaviour of ziPython ``subscribe`` command."""

    def unsubscribe(self, path: str) -> None:
        """Mirrors the behaviour of ziPython ``unsubscribe`` command."""


class Transaction:
    """Transaction Manager

    Buffers commands (node, value pairs)

    Args:
        nodetree: Underlying Nodetree
    """

    def __init__(self, nodetree: "NodeTree"):
        self._queue = None
        self._root = nodetree

    def start(self) -> None:
        """Start the transaction.

        Raises:
            Runtime Error if the transaction is already in progress
        """
        if self.in_progress():
            raise RuntimeError(
                "A transaction is already in progress. Only one transaction is "
                "possible at a time."
            )
        self._queue = []

    def stop(self) -> None:
        """Stop the transaction."""
        self._queue = None

    def add(self, node: t.Union[Node, str], value: t.Any) -> None:
        """Adds a single node set command to the set transaction.

        Args:
            node: Node object or string representing the node.
            value: Value that should be set to the node.

        Raises:
            AttributeError: If no transaction is in progress.
            ValueError: If the node is passed as a string in form of a relative
                path and no prefix can be added.
        """
        try:
            self._queue.append((self._root.to_raw_path(node), value))
        except AttributeError as exception:
            raise AttributeError("No set transaction is in progress.") from exception

    def in_progress(self) -> bool:
        """Flag if the transaction is in progress."""
        return self._queue is not None

    def result(self) -> t.List[t.Tuple]:
        """Resulting transaction list.

        Result:
            List of all added node value pairs.
        """
        return self._queue


class NodeTree:
    """High-level generic lazy node tree.

    All interactions with an Zurich Instruments device or a LabOne
    module happens through manipulating nodes. The ``NodeTree`` provides a
    pythonic way for that.

    It reads all available nodes its additional information from the provided
    connection and makes them available in nested dictionary like interface. The
    interface also supports accessing the nodes by attribute.

    >>> nodetree = NodeTree(connection)
    >>> nodetree.example.nodes[8].test
        /example/nodes/8/test

    To speed up the initialisation time the node tree is initialised lazy.
    Meaning the dictionary is kept as a flat dictionary and is not converted
    into a nested one. In addition the nested node objects returned by the
    ``NodeTree`` also are just simple placeholders. Only when performing
    operations on a node its validity is checked an the calls get translated to
    the correct node string. (For more information on how to manipulate nodes
    refer to :class:`zhinst.toolkit.nodetree.node.Node`).

    Examples:
        >>> nodetree = NodeTree(daq)
        >>> nodetree.dev123.demods[0].freq
        /dev123/demods/0/freq
        >>> nodetree = NodeTree(daq, prefix_hide = "dev123", list_nodes = ["/dev123/*"])
        >>> nodetree.demods[0].freq
        /dev123/demods/0/freq

    Args:
        connection: Underlying connection for the node tree. All
            operations are converted into calls to that connection.
        prefix_hide: Prefix, e.g. device id, that should be hidden in the
            nodetree. (Hidden means that users do not need to specify it and it
            will be added automatically to the nodes if necessary)
            (default = None)
        list_nodes: List of nodes that should be downloaded from the connection.
            By default all available nodes are downloaded. (default = None)
        preloaded_json: Optional preloaded node information.
            (e.g for the HF2 that does not support the `listNodesJson` function)
    """

    def __init__(
        self,
        connection: Connection,
        prefix_hide: str = None,
        list_nodes: list = None,
        preloaded_json: dict = None,
    ):
        self._prefix_hide = prefix_hide.lower() if prefix_hide else None
        self._connection = connection
        if not list_nodes:
            list_nodes = ["*"]
        if preloaded_json:
            self._flat_dict = preloaded_json
        else:
            self._flat_dict = {}
            for element in list_nodes:
                nodes_json = self.connection.listNodesJSON(element)
                self._flat_dict = {**self._flat_dict, **json.loads(nodes_json)}
        self._flat_dict = {key.lower(): value for key, value in self._flat_dict.items()}
        self._transaction = Transaction(self)
        # First Layer must be generate during initialisation to calculate the
        # prefixes to keep
        self._first_layer = []
        self._prefixes_keep = []
        self._generate_first_layer()

    def __getattr__(self, name):
        if not name.startswith("_"):
            return Node(self, (name.lower(),))
        return None

    def __getitem__(self, name):
        name = name.lower()
        if "/" in name:
            name_list = name.split("/")
            if name_list[0]:
                return Node(self, (*name_list,))
            return Node(self, (*name_list[1:],))
        return Node(self, (name,))

    def __contains__(self, k):
        return k.lower() in self._first_layer

    def __dir__(self):
        return self._first_layer

    def __iter__(self):
        for node_raw, info in self._flat_dict.items():
            yield self.raw_path_to_node(node_raw), info

    def _generate_first_layer(self) -> None:
        """Generates the internal ``_first_layer`` list.

        The list represents the available first layer of nested nodes.

        Also create the self._prefixes_keep variable. Which is the inverse of
        the self._prefix_hide attribute.

        Raises:
            SyntaxError: If any node does not start with a leading slash.
        """
        for raw_node in self._flat_dict:
            if not raw_node.startswith("/"):
                raise SyntaxError(f"{raw_node}: Leading slash not found")
            node_split = raw_node.split("/")
            # Since we always have a leading slash we ignore the first element
            # which is empty.
            if node_split[1] == self._prefix_hide:
                if node_split[2] not in self._first_layer:
                    self._first_layer.append(node_split[2])
            else:
                if node_split[1] not in self._prefixes_keep:
                    self._prefixes_keep.append(node_split[1])
        self._first_layer.extend(self._prefixes_keep)

    def get_node_info(self, node: t.Union[Node, str]) -> t.Dict[Node, t.Dict]:
        """Get the information/data for a node.

        Unix shell-style wildcards are supported.

        Args:
            node: Node object or string representation.

        Returns:
            Node(s) information.

        Raises:
            KeyErrror if the node does not match an existing node.
            ValueError: If the node is passed as a string in form of a relative
                path and no perfix can be added.
        """
        key = self.to_raw_path(node)
        # resolve potential wildcards
        keys = fnmatch.filter(self._flat_dict.keys(), key)
        result = {}
        for single_key in keys:
            result[self.raw_path_to_node(single_key)] = self._flat_dict.get(single_key)
        if not result:
            raise KeyError(key)
        return result

    def update_node(
        self,
        node: t.Union[Node, str],
        updates: t.Dict[str, t.Any],
        *,
        add: bool = False,
    ) -> None:
        """Update a node in the NodeTree.

        Nodes containing wildcards will be resolved but it is not possible to
        add new nodes with a ``node`` argument containing wildcards.

        Args:
            node: Node object or string representation.
            updates: Data that will be updated (overwrites the existing values).
            add: Flag a non-existing node should be added (default = False).

        Raises:
            KeyError: If node does not exist and the ``add`` Flag is not set
            ValueError: If the node is passed as a string in form of a relative
                path and no perfix can be added.
        """
        potential_key = self.to_raw_path(node).lower()
        # resolve potential wildcards
        keys = fnmatch.filter(self._flat_dict.keys(), potential_key)
        if not keys:
            if not add:
                raise KeyError(potential_key)
            if any(wildcard in potential_key for wildcard in ["*", "?", "["]):
                # Can be implemented in the future if necessary
                raise RuntimeError(
                    f"{potential_key}: Unable to resolve wildcards when adding "
                    "new nodes."
                )
            self._flat_dict[potential_key] = updates
            first_node = potential_key.split("/")[1]
            if not self._prefix_hide == first_node:
                self._prefixes_keep.append(first_node)
                self._first_layer.append(first_node)
        else:
            for single_key in keys:
                self._flat_dict[single_key].update(updates)
        Node.node_info.fget.cache_clear()

    def update_nodes(
        self,
        update_dict: t.Dict[t.Union[Node, str], t.Dict[str, t.Any]],
        *,
        add: bool = False,
    ) -> None:
        """Update multiple nodes in the NodeTree.

        Similar to :func:`update_node` but for multiple elements that are
        represented as a dict.

        Args:
            update_dict: Dictionary with node as keys and entries that will be
                updated as values.
            add: Flag a non-existing node should be added (default = False).

        Raises:
            KeyError: If node does not exist and the ``add`` flag is not set
        """
        for node, updates in update_dict.items():
            self.update_node(node, updates, add=add)

    def raw_path_to_node(self, raw_path: str) -> Node:
        """Converts a raw node path string into a Node object.

        The function does not check if the node exists, but if the node exist
        the returned node does correspond also to that node.

        Args:
            raw_path: Raw node path (e.g. /dev1234/relative/path/to/node).

        Returns:
            The corresponding node object linked to this nodetree.
        """
        node_split = raw_path.split("/")
        # buildin keywords are escaped with a tailing underscore
        # (https://pep8.org/#descriptive-naming-styles)
        node_split = [
            element + "_" if is_keyword(element) else element for element in node_split
        ]
        # Since we always have a leading slash we ignore the first element
        # which is empty.
        if node_split[1] == self._prefix_hide:
            return Node(self, (*node_split[2:],))
        return Node(self, (*node_split[1:],))

    def to_raw_path(self, node: t.Union[Node, str]) -> str:
        """Converts a node into a raw node path string.

        The function does not check if the node exists, but if the node exist
        the returned raw node path exists in the underlying dictionary.

        Args:
            node: Node object or string representing the node.

        Returns:
            Raw node path that can be used a key in the internal dictionary.

        Raises:
            ValueError: If the node is passed as a string in form of a relative
            path and no prefix can be added.
        """
        return (
            self.node_to_raw_path(node)
            if isinstance(node, Node)
            else self.string_to_raw_path(node)
        )

    def node_to_raw_path(self, node: Node) -> str:
        """Converts a node into a raw node path string.

        The function does not check if the node exists, but if the node exist
        the returned raw node path exists in the underlying dictionary.

        Args:
            node: Node object.

        Returns:
            Raw node path that can be used a key in the internal dictionary.
        """
        if not node.raw_tree:
            return "/" + self._prefix_hide if self._prefix_hide else "/"
        # buildin keywords are escaped with a tailing underscore
        # (https://pep8.org/#descriptive-naming-styles)
        node_list = [element.rstrip("_") for element in node.raw_tree]
        if node_list[0] in self._prefixes_keep:
            string_list = "/".join(node_list)
        else:
            try:
                string_list = "/".join([self._prefix_hide] + node_list)
            except TypeError:
                string_list = "/".join(node_list)
        return "/" + string_list

    def string_to_raw_path(self, node: str) -> str:
        """Converts a string representation of a node into a raw node path string.

        The function does not check if the node exists, but if the node exist
        the returned raw node path exists in the underlying dictionary.

        If the string does not represent a absolute path (leading slash) the
        :obj:`prefix_hide` will be added to the node string.

        Args:
            node: A string representation of the node.

        Returns:
            Raw node path that can be used a key in the internal dictionary.

        Raises:
            ValueError: If the node is a relative path and no perfix can be
                added.
        """
        if not node.startswith("/"):
            try:
                return "/" + self._prefix_hide + "/" + node
            except TypeError as error:
                raise ValueError(
                    f"{node} is a relative path but should be a "
                    "absolute path (leading slash)"
                ) from error
        return node

    @contextmanager
    def set_transaction(self) -> t.Generator[None, None, None]:
        """Context manager for a transactional set.

        Can be used as a context in a with statement and bundles all node set
        commands into a single transaction. This reduces the network overhead
        and often increases the speed.

        Within the with block all set commands to a node will be buffered
        and bundeld into a single command at the end of the context
        automatically. (All other operations, e.g. getting the value of a node,
        will not be affected)

        Warning:
            The set is always performed as deep set if called on device nodes.

        Examples:
            >>> with nodetree.set_transaction():
                    nodetree.test[0].a(1)
                    nodetree.test[1].a(2)
        """
        self._transaction.start()
        try:
            yield
            self.connection.set(self._transaction.result())
        finally:
            self._transaction.stop()

    @property
    def transaction(self) -> Transaction:
        """Transaction manager."""
        return self._transaction

    @property
    def connection(self) -> Connection:
        """Underlying connection."""
        return self._connection

    @property
    def prefix_hide(self) -> str:
        """Prefix (e.g device id), that is hidden in the nodetree.

        Hidden means that users do not need to specify it and it will be added
        automatically to the nodes if necessary.
        """
        return self._prefix_hide

    @property
    def raw_dict(self) -> dict:
        """Underlying flat dictionary with all node information."""
        return self._flat_dict
