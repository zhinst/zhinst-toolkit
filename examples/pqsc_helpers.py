import zhinst.toolkit.driver.devices as devices
from zhinst.toolkit.driver.devices.pqsc import PQSC


def find_zsync_worker_port(pqsc: PQSC, device: devices.DeviceType) -> int:
    """Find the ID of the PQSC ZSync port connected to a given device.

    Args:
        pqsc: PQSC device over whose ports the research shall be done.
        device: device for which the connected ZSync port shall be found.

    Returns:
        Integer value represent the ID of the searched PQSC Zsync port.

    """
    node_to_serial_dict = pqsc.zsyncs["*"].connection.serial()
    serial_to_node_dict = {v: k for k, v in node_to_serial_dict.items()}
    device_serial = device.serial[3:]
    # Get the node of the ZSync connected to the device
    # (will have the form "/devXXXX/zsyncs/N/connection/serial")
    try:
        device_zsync_node = serial_to_node_dict[device_serial]
    except KeyError:
        raise Exception(
            f"No ZSync connection found between the PQSC {pqsc.serial} and the device {device.serial}."
        )
    # Just interested in knowing N: split in
    # ['', 'devXXXX', 'zsyncs', 'N', 'connection', 'serial']
    # and take fourth value
    device_zsync_port = int(device_zsync_node.split("/")[3])

    return device_zsync_port
