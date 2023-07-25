from zhinst.toolkit import Session
from zhinst.toolkit.driver.nodes.awg import AWG
import enum
from typing import Optional
from dataclasses import dataclass
import numpy as np


class LogType(enum.Enum):
    Error = enum.auto()
    Trigger = enum.auto()
    ZSync_Feedback = enum.auto()
    Internal_Feedback = enum.auto()
    ZSync_AUX = enum.auto()
    DIO = enum.auto()


class TriggerSource(enum.Flag):
    DigTrigger1 = enum.auto()
    DigTrigger2 = enum.auto()
    ZSyncTrigger = enum.auto()


@dataclass
class LogEntry:
    time_clk: int
    time_us: float
    log_type: LogType
    trigger_source: Optional[TriggerSource] = None
    raw: Optional[int] = None
    processed1: Optional[int] = None
    processed2: Optional[int] = None
    addr: Optional[int] = None
    data: Optional[int] = None

    def __str__(self):
        entry_str = f"{self.time_clk:<7d}\t{self.time_us:.3f}\t{self.log_type.name:s} "

        if self.log_type == LogType.Error:
            entry_str += "Collision error"
        if self.log_type == LogType.Trigger:
            entry_str += f"source({self.trigger_source.name:s})"
        elif (
            self.log_type == LogType.ZSync_Feedback
            and self.processed1 is not None
            and self.processed2 is not None
        ):
            entry_str += f"raw(0x{self.raw:04X}) register(0x{self.processed1:04X}) decoder(0x{self.processed2:04X})"
        elif self.log_type == LogType.ZSync_Feedback:
            entry_str += f"raw(0x{self.raw:04X})"
        elif self.log_type == LogType.Internal_Feedback:
            entry_str += f"raw(0x{self.raw:04X}) processed(0x{self.processed1:04X})"
        elif self.log_type == LogType.ZSync_AUX:
            entry_str += f"addr(0x{self.addr:04X}) data(0x{self.data:08X})"
        elif self.log_type == LogType.DIO:
            entry_str += f"raw(0x{self.raw:08X})"
        else:
            raise RuntimeError("Unknown log type!")

        return entry_str


def reset_and_enable_rtlogger(
    awg: AWG, input: str = "zsync", start_timestamp: Optional[int] = None
) -> None:
    """Reset and start a given RT Logger.

    Args:
        awg: AWG node of the RTLogger
        input: The source of data that it should log. Either "dio" or "zsync". (default: "zsync")
        start_timestamp: optional start timestamp, if provided, timestamp mode is used.

    """
    awg.rtlogger.clear(True)  # Clear the logs
    if start_timestamp is None:
        # Starts with the AWG and overwrites old values as soon as the memory limit
        # is reached.
        awg.rtlogger.mode("normal")
    else:
        # Starts with the AWG, waits for the first valid trigger, and only starts
        # recording data after the time specified by the start_timestamp.
        # Recording stops as soon as the memory limit is reached.
        awg.rtlogger.mode("timestamp")
        awg.rtlogger.starttimestamp(start_timestamp)

    # Set the input of the rtlogger
    # This is necessary only on the SHF family,
    # on the HDAWG such node is absent, since the input
    # is selected by the node dios/0/mode
    if awg.rtlogger.input:
        awg.rtlogger.input(input)

    # Start the rtlogger
    awg.rtlogger.enable(True, deep=True)


def _get_trigdelay(session: Session, awg: AWG) -> int:
    """Get the ZSync trigger delay.

    Note: this function makes use of a raw node; raw nodes are usually meant for
    internal purposes only, they are not documented and their existence is not
    guaranteed in future releases. This function is intended for illustrative
    purposes only and raw nodes should not be used by users.

    Args:
        session: Toolkit session to a data server.
        awg: AWG node.

    Returns:
        The delay of the ZSync trigger, in clock cycles.

    """
    awg_split = str(awg).split("/")  # Split into list
    awg_split.insert(2, "raw")
    awg_split.append("zsync")
    awg_split.append("trigdelay")
    trigdelay_node = "/".join(awg_split)  # Join again into node path

    trig_delay = session.daq_server.getInt(trigdelay_node)

    # The trigger delay on the SG and QA channels is in 500 MHz unit
    if "sgchannels" in str(awg) or "qachannels" in str(awg):
        trig_delay = int(np.ceil(trig_delay / 2))

    return trig_delay


def print_rtlogger_data(
    session: Session,
    awg: AWG,
    compensate_start_trigger: bool = True,
    max_lines: int = None,
    silent: bool = False,
) -> Optional[list[LogEntry]]:
    """Print the data collected by the RT Logger.

    Args:
        session: Toolkit session to a data server.
        awg: AWG node
        compensate_start_trigger: True if the start trigger delay should
            be compensated for.
        max_lines: Maximum number of lines to be printed.
        silent: if True - don't print anything, return the
            list of events. (Default: False)

    Returns:
        list[LogEntry]: list of logged events, if silent is True, otherwise None

    """
    rtlogger = awg.rtlogger

    # Fetch the output of the rtlogger and decode
    rtdata = rtlogger.data().reshape((-1, 4))
    rtdata.dtype = np.dtype(
        [
            ("timestamp", np.int64),
            ("value", np.int64),
            ("source", np.int64),
            ("error", np.int64),
        ]
    )

    # Get various parameter
    timebase = rtlogger.timebase()

    reg_node = awg.zsync.register
    if reg_node:
        reg_shift, reg_mask, reg_offset = (
            reg_node.shift(),
            reg_node.mask(),
            reg_node.offset(),
        )
    else:
        reg_shift, reg_mask, reg_offset = (0, 0, 0)

    dec_node = awg.zsync.decoder
    if dec_node:
        dec_shift, dec_mask, dec_offset = (
            dec_node.shift(),
            dec_node.mask(),
            dec_node.offset(),
        )
    else:
        dec_shift, dec_mask, dec_offset = (0, 0, 0)

    intfeedback_node = awg.intfeedback.direct
    if intfeedback_node:
        int_shift, int_mask, int_offset = (
            intfeedback_node.shift(),
            intfeedback_node.mask(),
            intfeedback_node.offset(),
        )
    else:
        int_shift, int_mask, int_offset = (0, 0, 0)

    if compensate_start_trigger:
        trig_delay = _get_trigdelay(session, awg)
    else:
        trig_delay = 0
    base_ts = 0

    # Process the raw data
    max_lines = max_lines or len(rtdata)
    entries = []
    for i in range(max_lines):
        line = rtdata[i]
        raw_value = int(line["value"])

        # the +2 is due to the difference between the
        # rtlogger and the sequencer behavior
        ts = int(line["timestamp"]) - base_ts + 2
        ts_s = ts * timebase * 1e6

        # Check collision error
        if line["error"]:
            entry = LogEntry(ts, ts_s, LogType.Error)
            entries.append(entry)
            continue

        # - Trigger processing
        trigger_source = TriggerSource(0)
        if line["source"] == 2:
            # Dig trigger 1
            if raw_value & 0x40000000:
                trigger_source |= TriggerSource.DigTrigger1
            # Dig trigger 2
            if raw_value & 0x80000000:
                trigger_source |= TriggerSource.DigTrigger2
            # ZSync trigger
            if (raw_value & 0xC0000000) == 0 and (raw_value & 0xFF) == 0x08:
                trigger_source = TriggerSource.ZSyncTrigger

        if bool(trigger_source):
            # Reset the time counter if requested
            if compensate_start_trigger:
                base_ts = int(line["timestamp"]) + trig_delay
                ts = 0
                ts_s = 0.0
            else:
                ts = int(line["timestamp"])
                ts_s = ts * timebase * 1e6

            # We got a trigger, save it
            entry = LogEntry(ts, ts_s, LogType.Trigger, trigger_source=trigger_source)
            entries.append(entry)
            continue

        # - ZSync feedback processing
        if line["source"] == 1:
            if reg_node and dec_node:
                register_data = ((raw_value >> reg_shift) & reg_mask) + reg_offset
                decoder_data = ((raw_value >> dec_shift) & dec_mask) + dec_offset
                entry = LogEntry(
                    ts,
                    ts_s,
                    LogType.ZSync_Feedback,
                    raw=raw_value,
                    processed1=register_data,
                    processed2=decoder_data,
                )
            else:
                entry = LogEntry(ts, ts_s, LogType.ZSync_Feedback, raw=raw_value)
            entries.append(entry)
            continue

        # - Internal feedback processing
        if line["source"] == 3:
            processed_data = ((raw_value >> int_shift) & int_mask) + int_offset
            entry = LogEntry(
                ts,
                ts_s,
                LogType.Internal_Feedback,
                raw=raw_value,
                processed1=processed_data,
            )
            entries.append(entry)
            continue

        # - DIO processing
        if line["source"] == 0:
            entry = LogEntry(ts, ts_s, LogType.DIO, raw=raw_value)
            entries.append(entry)
            continue

        # - ZSync AUX processing
        if (
            line["source"] == 2
            and (raw_value & 0xC0000000) == 0
            and (raw_value & 0xFF) == 0x01
        ):
            addr = (raw_value >> 8) & 0xFFFF
            data = (raw_value >> 16) & 0x3FFF
            entry = LogEntry(ts, ts_s, LogType.ZSync_AUX, addr=addr, data=data)
            entries.append(entry)
            continue

    if silent:
        return entries
    else:
        # Print the RTLogger logs
        print("t[clk]\tt[us]\tData")
        for entry in entries:
            print(entry)
        return None  # Avoid dump to console in interactive session
