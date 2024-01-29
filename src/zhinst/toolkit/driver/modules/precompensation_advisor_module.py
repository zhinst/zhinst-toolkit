"""Precompensation Advisor Module."""
import logging
import typing as t
from functools import partial

from zhinst.core import PrecompensationAdvisorModule as TKPrecompensationAdvisorModule
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.driver.modules.base_module import BaseModule

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session


class PrecompensationAdvisorModule(Node):
    """Precompensation Advisor Module.

    This module provides the functionality available in the LabOne User
    Interface’s Precompensation Tab. In essence the precompensation allows a
    pre-distortion or pre-emphasis to be applied to a signal before it leaves
    the instrument, to compensate for undesired distortions caused by the
    device under test (DUT). The Precompensation Advisor module simulates the
    precompensation filters in the device, allowing the user to experiment with
    different filter settings and filter combinations to obtain an optimal
    output signal, before using the setup in the actual device.

    For a complete documentation see the LabOne user manual
    https://docs.zhinst.com/labone_api_user_manual/modules/precompensation_advisor/index.html

    Note:
        Unlike most other LabOne modules, this module does not expose any
        functions. Each time one or more filter parameters are changed, the
        module re-runs the simulation and the results can be read via the
        wave/output, wave/output/forwardwave and wave/output/backwardwave
        parameters.

    Args:
        raw_module: zhinst.core module.
        session: Session to the Data Server.
    """

    def __init__(self, raw_module: TKPrecompensationAdvisorModule, session: "Session"):
        self._raw_module = raw_module
        self._session = session
        super().__init__(NodeTree(raw_module), tuple())
        self.root.update_nodes(
            {
                "/device": {
                    "GetParser": partial(BaseModule._get_device, self._session),
                    "SetParser": BaseModule._set_device,
                }
            },
            raise_for_invalid_node=False,
        )

    def __repr__(self):
        return str(f"{self._raw_module.__class__.__name__}({repr(self._session)})")

    @property
    def raw_module(self) -> TKPrecompensationAdvisorModule:
        """Underlying core module."""
        return self._raw_module
