# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.


from zhinst.ziPython import ziDiscovery
from zhinst.toolkit import HDAWG, UHFQA, UHFLI, MFLI, PQSC, SHFQA, SHFSG
from zhinst.toolkit.control.drivers.base.base import (
    BaseInstrument,
    _logger as baseinstrument_logger,
)
from zhinst.toolkit.control.drivers.base.awg import AWGCore, _logger as awg_logger
from zhinst.toolkit.control.drivers.base.scope import Scope, _logger as scope_logger
from zhinst.toolkit.control.drivers.base.daq import (
    DAQModule,
    _logger as daq_logger,
)
from zhinst.toolkit.control.drivers.base.sweeper import (
    SweeperModule,
    _logger as sweeper_logger,
)
from zhinst.toolkit.control.drivers.uhfqa import (
    AWG as UHFQA_AWG,
    ReadoutChannel,
    _logger as uhfqa_logger,
)
from zhinst.toolkit.control.drivers.hdawg import (
    AWG as HDAWG_AWG,
    _logger as hdawg_logger,
)
from zhinst.toolkit.control.drivers.shfsg import (
    SGChannel as SHFSG_Channel,
    _logger as shfsg_logger,
)
from zhinst.toolkit.control.drivers.shfqa import (
    QAChannel as SHFQA_Channel,
    Generator as SHFQA_Generator,
    Sweeper as SHFQA_Sweeper,
    Scope as SHFQA_Scope,
    _logger as shfqa_logger,
)
from zhinst.toolkit.control.drivers.pqsc import _logger as pqsc_logger
from zhinst.toolkit.control.drivers.mfli import (
    DAQModule as DAQModule_MFLI,
    SweeperModule as Sweeper_MFLI,
)
from zhinst.toolkit.control.drivers.uhfli import (
    DAQModule as DAQModule_UHFLI,
    SweeperModule as Sweeper_UHFLI,
    _logger as uhfli_logger,
)
from zhinst.toolkit.control.connection import (
    ZIConnection,
    DeviceConnection,
    _logger as connection_logger,
)
from zhinst.toolkit.control.node_tree import (
    NodeTree,
    Parameter,
    NodeList,
    Node,
    _logger as nodetree_logger,
)
from zhinst.toolkit.control.parsers import Parse, _logger as parser_logger
from zhinst.toolkit.helpers.sequence_commands import (
    SequenceCommand,
    _logger as sequence_command_logger,
)
from zhinst.toolkit.helpers.sequences import _logger as sequences_logger
from zhinst.toolkit.helpers.waveform import Waveform, _logger as waveform_logger
from zhinst.toolkit.helpers import SequenceProgram
from zhinst.toolkit import SequenceType, TriggerMode, Alignment
from zhinst.toolkit.interface import (
    InstrumentConfiguration,
    DeviceTypes,
)
