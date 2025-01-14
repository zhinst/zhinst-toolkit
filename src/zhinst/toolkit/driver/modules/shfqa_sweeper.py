"""Toolkit adaption for the zhinst.utils.SHFSweeper."""

import json
import logging
import re
import typing as t
from collections import OrderedDict
from dataclasses import asdict
from enum import IntEnum
from pathlib import Path

import numpy as np
from zhinst.utils.shf_sweeper import AvgConfig, EnvelopeConfig, RfConfig
from zhinst.utils.shf_sweeper import ShfSweeper as CoreSweeper
from zhinst.utils.shf_sweeper import SweepConfig, TriggerConfig

from zhinst.toolkit.driver.parsers import Parse
from zhinst.toolkit.exceptions import ToolkitError
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.connection_dict import ConnectionDict
from zhinst.toolkit.nodetree.helper import NodeDoc

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.driver.devices import DeviceType
    from zhinst.toolkit.session import Session

logger = logging.getLogger(__name__)


class SHFQASweeper(Node):
    """Toolkit adaption for the zhinst.utils.SHFSweeper.

    For now the general sweeper module does not support the SHFQA. However a
    python based implementation called ``SHFSweeper`` does already provide
    this functionality. The ``SHFSweeper`` is part of the ``zhinst`` module
    and can be found in the utils.

    Toolkit wraps around the ``SHFSweeper`` and exposes a interface that is
    similar to the LabOne modules, meaning the parameters are exposed in a
    node tree like structure.

    All parameters can be accessed through their corresponding node:
    * device: Device to run the sweeper with
    * sweep: Frequency range settings for a sweep
    * rf: RF in- and output settings for a sweep
    * average: Averaging settings for a sweep
    * trigger: Settings for the trigger
    * envelope: Settings for defining a complex envelope for pulsed spectroscopy

    The underlying module is updated with the parameter changes automatically.
    Every functions from the underlying SHFSweeper module is exposed and can be
    used in the same way.

    Args:
        daq_server: Client Session that should be used by the sweeper.
        session: Session to the Data Server.
    """

    def __init__(self, session: "Session"):
        self._config_classes = {
            SweepConfig: ("sweep", "sweep_config"),
            RfConfig: ("rf", "rf_config"),
            AvgConfig: ("average", "avg_config"),
            TriggerConfig: ("trigger", "trig_config"),
            EnvelopeConfig: ("envelope", "envelope_config"),
        }
        self._renamed_nodes = {
            "imp50": "input_impedance",
            "use_sequencer": "mode",
            "force_sw_trigger": "sw_trigger_mode",
        }
        super().__init__(self._create_nodetree(), tuple())
        self._daq_server = session.clone_underlying_session()
        self._raw_module = CoreSweeper(self._daq_server, "")
        self._session = session
        self.root.update_nodes(
            {
                "/device": {
                    "GetParser": self._get_device,
                    "SetParser": self._set_device,
                },
                "/envelope/enable": {
                    "GetParser": Parse.to_bool,
                    "SetParser": Parse.from_bool,
                },
            },
            raise_for_invalid_node=False,
        )

    def __repr__(self):
        return str(f"SHFQASweeper({repr(self._session)})")

    def _get_device(self, serial: str) -> t.Union["DeviceType", str]:
        """Convert a device serial into a toolkit device object.

        Args:
            serial: Serial of the device

        Returns:
            Toolkit device object. If the serial does not
                match to a connected device the serial is returned instead.
        """
        try:
            return self._session.devices[serial]
        except (RuntimeError, KeyError):
            return serial

    def _set_device(self, value: t.Union["DeviceType", str]) -> str:
        """Convert a toolkit device object into a serial string.

        Args:
            value: Toolkit device object
                (can also be a serial string directly)

        Returns:
            Device serial
        """
        serial = ""
        try:
            serial = value.serial  # type: ignore
        except AttributeError:
            serial = value
        self._raw_module = CoreSweeper(self._daq_server, serial)
        return serial

    def _create_nodetree(self) -> NodeTree:
        """Create node tree for the SHFQA sweeper.

        Uses the hardcoded "resources/shfqa_sweeper_nodes.json" information
        and the SHFSweeper data classes to automatically create a valid node
        tree. (Automatically adds new parameters with dummy information)

        Returns:
            node tree for the shfqa sweeper
        """
        json_path = Path(__file__).parent / "../../resources/shfqa_sweeper_nodes.json"
        with json_path.open("r") as file:
            raw_info: NodeDoc = json.loads(file.read())
        values: t.Dict[str, t.Any] = {}
        info: NodeDoc = {}
        for config_class, parent_name in self._config_classes.items():
            for parameter, default_value in asdict(config_class()).items():
                node = (
                    f"/{parent_name[0]}/{self._renamed_nodes.get(parameter, parameter)}"
                )
                try:
                    info[node] = raw_info[node]
                except KeyError:
                    # node not in json
                    logger.warning(f"{node} is missing in {json_path}.")
                    type_mapping = {
                        int: "Integer (64 bit)",
                        float: "Double",
                        str: "String",
                        bool: "Integer (64 bit)",
                        np.ndarray: "ZIVectorData",
                    }
                    info[node] = {
                        "Node": node,
                        "Description": node,
                        "Properties": "Read, Write",
                        "Unit": "None",
                        "Type": type_mapping[type(default_value)],
                    }

                if "Options" in info[node]:
                    option_map = {}
                    for key, value in info[node]["Options"].items():
                        options = re.findall(r'"(.+?)"[,:]+', value)
                        option_map.update({x: int(key) for x in options})
                    values[node] = option_map.get(default_value, default_value)
                else:
                    values[node] = default_value
        info["/device"] = raw_info["/device"]
        values["/device"] = ""
        info["/envelope/enable"] = raw_info["/envelope/enable"]
        values["/envelope/enable"] = 0

        info["/actual_settling_time"] = raw_info["/actual_settling_time"]
        values["/actual_settling_time"] = lambda: self._raw_module.actual_settling_time
        info["/actual_hold_off_time"] = raw_info["/actual_hold_off_time"]
        values["/actual_hold_off_time"] = lambda: self._raw_module.actual_hold_off_time
        info["/predicted_cycle_time"] = raw_info["/predicted_cycle_time"]
        values["/predicted_cycle_time"] = lambda: self._raw_module.predicted_cycle_time

        return NodeTree(ConnectionDict(values, info))

    def _update_settings(self) -> None:
        """Update the ShfSweeper settings from the node tree.

        Converts the nodetree into a valid configuration for the SHFSweeper.
        """
        if not self.device():
            raise ToolkitError(
                "The device serial needs to be set before using the module."
            )
        data = OrderedDict()
        for config_class, parent_name in self._config_classes.items():
            config = OrderedDict()
            for parameter in asdict(config_class()):
                value = self[parent_name[0]][
                    self._renamed_nodes.get(parameter, parameter)
                ]()
                if isinstance(value, IntEnum):
                    value = value.name
                config[parameter] = value
            data[parent_name[1]] = config_class(**config)

        # special treatment for the envelope config
        if not self.envelope.enable():
            data.pop("envelope_config")

        # special treatment for the imp50
        try:
            data["trig_config"].imp50 = data["trig_config"].imp50 == "imp50"
        except AttributeError:
            logger.warning(
                "imp50 setting is no longer available in the shf_sweeper class."
            )
        # special treatment for mode
        try:
            data["sweep_config"].use_sequencer = (
                data["sweep_config"].use_sequencer == "sequencer-based"
            )
        except AttributeError:
            logger.warning(
                "use_sequencer setting is no longer available in the shf_sweeper class."
            )
        # special treatment for trigger source
        try:
            data["trig_config"].source = (
                data["trig_config"].source
                if data["trig_config"].source != "auto"
                else None
            )
        except AttributeError:
            logger.warning(
                "source setting is no longer available in the shf_sweeper class."
            )
        # special treatment for the force_sw_trigger
        try:
            data["trig_config"].force_sw_trigger = (
                data["trig_config"].force_sw_trigger == "force"
            )
        except AttributeError:
            logger.warning(
                "force_sw_trigger setting is no longer available in the shf_sweeper."
            )
        self._raw_module.configure(**data)

    def run(self) -> dict:
        """Perform a sweep with the specified settings.

        This method wraps around the `run` method of
        `zhinst.utils.shf_sweeper`

        Returns:
             A dictionary with measurement data of the last sweep.
        """
        self._update_settings()
        return self._raw_module.run()

    def get_result(self) -> dict:
        """Get the measurement data of the last sweep.

        This method wraps around the `get_result` method of
        `zhinst.utils.shf_sweeper`

        Returns:
             A dictionary with measurement data of the last sweep.
        """
        self._update_settings()
        return self._raw_module.get_result()

    def plot(self) -> None:
        """Plot power over frequency for last sweep.

        This method wraps around the `plot` method of
        `zhinst.utils.shf_sweeper`
        """
        self._update_settings()
        return self._raw_module.plot()

    def get_offset_freq_vector(self) -> t.Any:
        """Get vector of frequency points.

        This method wraps around the `get_offset_freq_vector` method of
        `zhinst.utils.shf_sweeper`

        Returns:
            Vector of frequency points.
        """
        self._update_settings()
        return self._raw_module.get_offset_freq_vector()
