from zhinst.toolkit import Session
from zhinst.toolkit.nodetree import Node
from zhinst.toolkit.driver.nodes.awg import AWG
from zhinst.core.errors import CoreError


def reset_and_enable_rtlogger(rtlogger: Node) -> None:
    """Reset and start a given RT Logger.

    Args:
        rtlogger: RT Logger node.

    """
    rtlogger.clear(True)
    rtlogger.mode(0)  # Start with first trigger
    try:
        rtlogger.input(
            0
        )  # Zsync input selected by diozsyncswitch node, set here to DIO
    except CoreError:
        pass  # Absent on HDAWG
    rtlogger.enable(True, deep=True)


def _get_trigdelay(session: Session, awg: AWG) -> int:
    """Get the ZSync trigger delay.

    Note: this function makes use of a raw node; raw nodes are usually meant for
    internal purposes only, they are not documented and their existence is not
    guaranteed in future releases. This function is intended for illustrative
    purposes only and raw nodes should not be used by customers.

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
    return session.daq_server.getInt(trigdelay_node)


def print_rtlogger_data(
    session: Session,
    awg: AWG,
    compensate_start_trigger: bool = True,
    max_lines: int = None,
) -> None:
    """Print the data collected by the RT Logger.

    Args:
        session: Toolkit session to a data server.
        awg: AWG node
        compensate_start_trigger: True if the start trigger delay should
            be compensated for.
        max_lines: Maximum number of lines to be printed.

    """
    rtlogger = awg.rtlogger
    rtdata = rtlogger.data()
    timebase = rtlogger.timebase()

    reg_shift = awg.zsync.register.shift()
    reg_mask = awg.zsync.register.mask()
    reg_offset = awg.zsync.register.offset()

    dec_shift = awg.zsync.decoder.shift()
    dec_mask = awg.zsync.decoder.mask()
    dec_offset = awg.zsync.decoder.offset()

    trig_delay = _get_trigdelay(session, awg)
    base_ts = 0

    max_lines = len(rtdata) // 2 if max_lines is None else max_lines

    print("t[clk]\tt[us]\tdata\tdata binary\t\tregister data\tdecoder data")
    for i in range(max_lines):

        # raw data
        data = rtdata[2 * i + 1]

        if compensate_start_trigger:
            # start trigger, reset timestamp
            if data == 0xFFFF:
                base_ts = rtdata[2 * i]
                ts = 0
            else:
                ts = int(rtdata[2 * i] - base_ts - trig_delay)
        else:
            ts = rtdata[2 * i]

        # calculate data after transformation
        reg_data_raw = (int(data) >> 8) & 0xF
        register_data = ((reg_data_raw >> reg_shift) & reg_mask) + reg_offset
        dec_data_raw = int(data) & 0xFF
        decoder_data = ((dec_data_raw >> dec_shift) & dec_mask) + dec_offset

        print(
            f"{ts:<7d}\t{ts*timebase*1e6:.3f}\t{data:<5d}\t0b{data:016b}\t{register_data:<5d}\t\t{decoder_data:<5d}"
        )
