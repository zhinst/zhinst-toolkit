"""Base Instrument Driver.

Natively works with all device types and provides the basic functionality like
the device specific nodetree.
"""
import copy
import json
import logging
import re
import typing as t
import warnings
from pathlib import Path

from zhinst.utils._version import version as utils_version_str
from zhinst.core import __version__ as zhinst_version_str

from zhinst.toolkit._min_version import _MIN_DEVICE_UTILS_VERSION, _MIN_LABONE_VERSION
from zhinst.toolkit.driver.parsers import node_parser
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import lazy_property
from zhinst.toolkit.exceptions import ToolkitError


logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:  # pragma: no cover
    from zhinst.toolkit.session import Session


class BaseInstrument(Node):
    """Generic toolkit driver for a Zurich Instrument device.

    All device specific class are derived from this class.
    It exposes the nodetree and also implements common functions valid for all
    devices.
    It also can be used directly, e.g. for instrument types that have no special
    class in toolkit.

    Args:
        serial: Serial number of the device, e.g. *'dev12000'*.
            The serial number can be found on the back panel of the instrument.
        device_type: Type of the device.
        session: Session to the Data Server
    """

    def __init__(
        self,
        serial: str,
        device_type: str,
        session: "Session",
    ):
        self._serial = serial
        self._device_type = device_type
        self._session = session
        try:
            self._options = session.daq_server.getString(f"/{serial}/features/options")
        except RuntimeError:
            self._options = ""

        # HF2 does not support listNodesJSON so we have the information hardcoded
        # (the node of HF2 will not change any more so this is safe)
        preloaded_json = None
        if "HF2" in self._device_type:
            preloaded_json = self._load_preloaded_json(
                Path(__file__).parent / "../../resources/nodedoc_hf2.json"
            )

        self._streaming_nodes: t.Optional[t.List[Node]] = None

        nodetree = NodeTree(
            self._session.daq_server,
            prefix_hide=self._serial,
            list_nodes=[f"/{self._serial}/*"],
            preloaded_json=preloaded_json,
        )
        # Add predefined parseres (in node_parser) to nodetree nodes
        nodetree.update_nodes(
            node_parser.get(self.__class__.__name__, {}), raise_for_invalid_node=False
        )

        super().__init__(nodetree, tuple())

    def __repr__(self):
        options = f"({self._options})" if self._options else ""
        options = options.replace("\n", ",")
        return str(
            f"{self.__class__.__name__}({self._device_type}" f"{options},{self.serial})"
        )

    def factory_reset(self, *, deep: bool = True, timeout: int = 30) -> None:
        """Load the factory default settings.

        Args:
            deep: A flag that specifies if a synchronization
                should be performed between the device and the data
                server after loading the factory preset (default: True).
            timeout: Timeout in seconds to wait for the factory reset to
                complete.

        Raises:
            ToolkitError: If the factory preset could not be loaded.
            TimeoutError: If the factory reset did not complete within the
                given timeout.
        """
        self.system.preset.load(1, deep=deep)
        self.system.preset.busy.wait_for_state_change(0, timeout=timeout)
        if self.system.preset.error(deep=True)[1]:
            raise ToolkitError(
                f"Failed to load factory preset to device {self.serial.upper()}."
            )
        logger.info(f"Factory preset is loaded to device {self.serial.upper()}.")

    @staticmethod
    def _version_string_to_tuple(version: str) -> t.Tuple[int, int, int]:
        """Converts a version string into a version tuple.

        Args:
            version: Version

        Returns:
            Version as a tuple of ints
        """
        result = [0] * 3
        for i, value in enumerate(version.split(".")):
            try:
                result[i] = int(value)
            except ValueError:
                if i < 3:  # ignore dev verisons
                    result[i] = 0
        return result[0], result[1], result[2]

    @staticmethod
    def _check_python_versions(
        zi_python_version: t.Tuple[int, int, int],
        zi_utils_version: t.Tuple[int, int, int],
    ) -> None:
        """Check if the minimum required zhinst packages are installed.

        Checks if all zhinst packages that toolkit require have the minimum
        required version installed.

        Args:
            zi_python_version: zhinst.core package version
            zi_utils_version: zhinst.utils package version

        Raises:
            ToolkitError: If the zhinst.core version does not match the
                minimum requirements for zhinst.toolkit
            ToolkitError: If the zhinst.utils version does not match the
                minimum requirements for zhinst.toolkit
        """
        if zi_python_version < BaseInstrument._version_string_to_tuple(
            _MIN_LABONE_VERSION
        ):
            raise ToolkitError(
                "zhinst.core version does not match the minimum required version "
                f"for zhinst.toolkit {zi_python_version} < {_MIN_LABONE_VERSION}. "
                "Use `pip install --upgrade zhinst` to get the latest version."
            )
        if zi_utils_version < BaseInstrument._version_string_to_tuple(
            _MIN_DEVICE_UTILS_VERSION
        ):
            raise ToolkitError(
                "zhinst.utils version does not match the minimum required "
                f"version for zhinst.toolkit {zi_utils_version} < "
                f"{_MIN_DEVICE_UTILS_VERSION}. Use `pip install "
                "--upgrade zhinst.utils` to get the latest version."
            )

    @staticmethod
    def _check_labone_version(
        zi_python_version: t.Tuple[int, int, int],
        labone_version: t.Tuple[int, int, int],
    ) -> None:
        """Check that the LabOne version matches the zhinst version.

        Args:
            zi_python_version: zhinst.core package version
            labone_version: LabOne DataServer version

        Raises:
            ToolkitError: If the zhinst.core version does not match the
                version of the connected LabOne DataServer.
        """
        if labone_version[:2] < zi_python_version[:2]:
            raise ToolkitError(
                "The LabOne version is smaller than the zhinst.core version. "
                f"{labone_version} < {zi_python_version}. "
                "Please install the latest/matching LabOne version from "
                "https://www.zhinst.com/support/download-center."
            )
        if labone_version[:2] > zi_python_version[:2]:
            raise ToolkitError(
                "the zhinst.core version is smaller than the LabOne version "
                f"{zi_python_version} < {labone_version}. "
                "Please install the latest/matching version from pypi.org."
            )
        if labone_version[-1] != zi_python_version[-1]:
            warnings.warn(
                "The patch version of zhinst.core and the LabOne DataServer "
                f"mismatch {labone_version[-1]} ! {zi_python_version[-1]}.",
                RuntimeWarning,
                stacklevel=2,
            )

    def _check_firmware_update_status(self) -> None:
        """Check if the firmware matches LabOne version.

        Raises:
            ConnectionError: If the device is currently updating
            ToolkitError: If the firmware revision does not match to the
                version of the connected LabOne DataServer.
        """
        device_info = json.loads(self._session.daq_server.getString("/zi/devices"))[
            self.serial.upper()
        ]
        status_flag = device_info["STATUSFLAGS"]
        if status_flag & 1 << 8:
            raise ConnectionError(
                "The device is currently updating please try again after the update "
                "process is complete"
            )
        if status_flag & 1 << 4 or status_flag & 1 << 5:
            raise ToolkitError(
                "The Firmware does not match the LabOne version. "
                "Please update the firmware (e.g. in the LabOne UI)"
            )
        if status_flag & 1 << 6 or status_flag & 1 << 7:
            raise ToolkitError(
                "The Firmware does not match the LabOne version. "
                "Please update LabOne to the latest version from "
                "https://www.zhinst.com/support/download-center."
            )

    def check_compatibility(self) -> None:
        """Check if the software stack is compatible.

        Only if all versions and revisions of the software stack match stability
        can be ensured. The following criteria are checked:

            * minimum required zhinst-utils package is installed
            * minimum required zhinst-core package is installed
            * zhinst package matches the LabOne Data Server version
            * firmware revision matches the LabOne Data Server version

        Raises:
            ConnectionError: If the device is currently updating
            ToolkitError: If one of the above mentioned criterion is not
                fulfilled
        """
        self._check_python_versions(
            self._version_string_to_tuple(zhinst_version_str),
            self._version_string_to_tuple(utils_version_str),
        )
        labone_version_str = self._session.about.version()
        labone_revision_str = str(self._session.about.revision())[4:]
        labone_version = self._version_string_to_tuple(
            labone_version_str + "." + labone_revision_str
        )
        self._check_labone_version(
            self._version_string_to_tuple(zhinst_version_str), labone_version
        )
        self._check_firmware_update_status()

    def get_streamingnodes(self) -> t.List[Node]:
        """Create a list with all streaming nodes available.

        Returns:
            Available streaming node.
        """
        if self._streaming_nodes is None:
            self._streaming_nodes = []
            for node, info in self:
                if "Stream" in info.get("Properties"):
                    self._streaming_nodes.append(node)
        return self._streaming_nodes

    def _load_preloaded_json(self, filename: Path) -> t.Optional[dict]:
        """Load a preloaded json and match the existing nodes.

        Args:
            Filename for the preloaded json.

        Returns:
            Loaded JSON if the file exists.
        """
        if not filename.is_file():
            return None
        raw_file = filename.open("r").read()

        raw_file = raw_file.replace("devxxxx", self.serial.lower())
        raw_file = raw_file.replace("DEVXXXX", self.serial.upper())
        json_raw = json.loads(raw_file)

        existing_nodes = self._session.daq_server.listNodes(
            f"/{self.serial}/*", recursive=True, leavesonly=True
        )

        preloaded_json = {}
        for node in existing_nodes:
            node_name = re.sub(r"(?<!values)\/[0-9]*?$", "/n", node.lower())
            node_name = re.sub(r"\/[0-9]*?\/", "/n/", node_name)
            json_element = copy.deepcopy(json_raw.get(node_name))
            if json_element:
                json_element["Node"] = node.upper()
                preloaded_json[node.lower()] = json_element
            elif not node.startswith("/zi/"):
                logger.warning(f"unkown node {node}")

        return preloaded_json

    def set_transaction(self) -> t.ContextManager:
        """Context manager for a transactional set.

        Can be used as a context in a with statement and bundles all node set
        commands into a single transaction. This reduces the network overhead
        and often increases the speed.

        Within the with block a set commands to a node will be buffered
        and bundled into a single command at the end automatically.
        (All other operations, e.g. getting the value of a node, will not be
        affected)

        Warning:
            The set is always performed as deep set if called on device nodes.

        Examples:
            >>> with device.set_transaction():
                    device.test[0].a(1)
                    device.test[1].a(2)
        """
        return self._root.set_transaction()

    @property
    def serial(self) -> str:
        """Instrument specific serial."""
        return self._serial

    @property
    def session(self) -> "Session":
        """Underlying session to the data server.

        .. versionadded:: 0.5.1
        """
        return self._session

    @property
    def device_type(self) -> str:
        """Type of the instrument (e.g. MFLI)."""
        return self._device_type

    @lazy_property
    def device_options(self) -> str:
        """Enabled options of the instrument."""
        return self.features.options()
