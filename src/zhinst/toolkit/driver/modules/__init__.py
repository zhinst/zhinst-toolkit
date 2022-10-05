"""Module for toolkit representations of native LabOne modules."""
import typing as t

from zhinst.toolkit.driver.modules.base_module import BaseModule
from zhinst.toolkit.driver.modules.daq_module import DAQModule
from zhinst.toolkit.driver.modules.shfqa_sweeper import SHFQASweeper
from zhinst.toolkit.driver.modules.sweeper_module import SweeperModule
from zhinst.toolkit.driver.modules.scope_module import ScopeModule

ModuleType = t.Union[BaseModule, DAQModule, SHFQASweeper, SweeperModule, ScopeModule]

__all__ = ["BaseModule", "DAQModule", "SHFQASweeper", "SweeperModule", "ScopeModule"]
