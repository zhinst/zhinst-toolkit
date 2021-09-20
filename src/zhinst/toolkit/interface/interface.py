# Copyright (C) 2020 Zurich Instruments
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENSE file for details.

import attr
from enum import Enum, auto
import logging
import traceback


class DeviceTypes(Enum):
    """Enum of device types."""

    HDAWG = "hdawg"
    UHFQA = "uhfqa"
    UHFLI = "uhfli"
    MFLI = "mfli"
    PQSC = "pqsc"
    SHFQA = "shfqa"
    SHFSG = "shfsg"


@attr.s
class ZIDeviceConfig:
    """Device configuration with serial, device_type and interface."""

    serial: str = attr.ib(default="dev#####")
    device_type: str = attr.ib(default=DeviceTypes.HDAWG)
    interface: str = attr.ib(default="1GbE")


class ZIDevice:
    """Device configuration with name and config."""

    def __init__(self):
        self._config = ZIDeviceConfig()
        self.name = "device0"

    @property
    def config(self):
        return self._config


@attr.s
class ZIAPI:
    """API configuration with host, port, api-level."""

    host: str = attr.ib(default="localhost")
    port: int = attr.ib(default=8004)
    api: int = attr.ib(default=6)


class InstrumentConfiguration:
    """Data structure used to for instrument and API configuration."""

    def __init__(self):
        self._api_config = ZIAPI()
        self._instrument = ZIDevice()

    @property
    def api_config(self):
        return self._api_config

    @property
    def instrument(self):
        return self._instrument


class LoggerModule:
    """Implement a custom logging module.

    Arguments:
        name (str): Name used to instantiate the logger object using
            the function `logging.getLogger(name)`. When the
            `LoggerModule` class is imported to another module,
            `__name__` should be used as argument.  That’s because in a
             module, `__name__` is the module’s name in the Python
             package namespace.

    """

    def __init__(self, name):
        self._name = name
        self._is_enabled = True
        self._custom_field = {"callername": ""}
        self._logger = logging.getLogger(self._name)
        self._syslog = logging.StreamHandler()
        self._formatter = logging.Formatter(
            "%(levelname)s: %(callername)s\n%(message)s"
        )
        self._syslog.setFormatter(self._formatter)
        self._logger.addHandler(self._syslog)
        self._logger = logging.LoggerAdapter(self._logger, self._custom_field)

    class ExceptionTypes(Enum):
        """Enum of exception types."""

        ToolkitConnectionError = auto()
        ToolkitNodeTreeError = auto()
        ToolkitError = auto()
        ValueError = auto()
        TypeError = auto()
        TimeoutError = auto()

    class ToolkitConnectionError(Exception):
        """Custom Exception class for ToolkitConnectionError"""

        pass

    class ToolkitNodeTreeError(Exception):
        """Custom Exception class for ToolkitNodeTreeError"""

        pass

    class ToolkitError(Exception):
        """Custom Exception class for ToolkitError"""

        pass

    def enable_logging(self):
        self._is_enabled = True

    def disable_logging(self):
        self._is_enabled = False

    @staticmethod
    def _get_caller():
        """Update the caller name.

        This method extracts the line attribute of the FrameSummary object
        with the name `<module>` . This line attribute corresponds to the line
        of code in the user notebook that eventually calls this function.
        """
        frame_list = traceback.StackSummary.extract(traceback.walk_stack(None))
        for frame in frame_list:
            if frame.name == "<module>":
                return frame.line

    def info(self, msg, *args, **kwargs):
        """Logs a message with level INFO on the log.

        Updates the caller name before logging the message and passes
        all arguments and keyword arguments to the underlying `info`
        method.

        Arguments:
            msg (str): The message string
        """
        if self._is_enabled:
            self._custom_field["callername"] = LoggerModule._get_caller()
            self._logger = logging.LoggerAdapter(self._logger, self._custom_field)
            self._logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Logs a message with level WARNING on the log.

        Updates the caller name before logging the message and passes
        all arguments and keyword arguments to the underlying `warning`
        method.

        Arguments:
            msg (str): The message string
        """
        if self._is_enabled:
            self._custom_field["callername"] = LoggerModule._get_caller()
            self._logger = logging.LoggerAdapter(self._logger, self._custom_field)
            self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, exception_type, *args, **kwargs):
        """Logs a message with level ERROR on the log.

        Updates the caller name before logging the message and passes
        all arguments and keyword arguments to the underlying `error`
        method. It eventually raises an exception depending on the
        exception type specified by the `exception_type` argument.

        Arguments:
            msg (str): The message string
            exception_type (class:`ExceptionTypes`): Type enum for the
                exception to be raised.

        """
        if self._is_enabled:
            self._custom_field["callername"] = LoggerModule._get_caller()
            self._logger = logging.LoggerAdapter(self._logger, self._custom_field)
            self._logger.error(msg, *args, **kwargs)
        if exception_type == LoggerModule.ExceptionTypes.ToolkitConnectionError:
            raise LoggerModule.ToolkitConnectionError(msg)
        elif exception_type == LoggerModule.ExceptionTypes.ToolkitNodeTreeError:
            raise LoggerModule.ToolkitNodeTreeError(msg)
        elif exception_type == LoggerModule.ExceptionTypes.ToolkitError:
            raise LoggerModule.ToolkitError(msg)
        elif exception_type == LoggerModule.ExceptionTypes.ValueError:
            raise ValueError(msg)
        elif exception_type == LoggerModule.ExceptionTypes.TypeError:
            raise TypeError(msg)
        elif exception_type == LoggerModule.ExceptionTypes.TimeoutError:
            raise TimeoutError(msg)
        else:
            raise Exception(msg)
