"""High-level generic lazy node tree for the zhinst.core package.

All interactions with an Zurich Instruments device or a LabOne
module happens through manipulating nodes. The
:class:`zhinst.toolkit.nodetree.nodetree.NodeTree` provides a pythonic way for
that.

>>> nodetree = NodeTree(connection)
>>> nodetree.example.nodes[8].test
    /example/nodes/8/test
"""

from zhinst.toolkit.nodetree.node import Node
from zhinst.toolkit.nodetree.nodetree import NodeTree


__all__ = ["Node", "NodeTree"]
