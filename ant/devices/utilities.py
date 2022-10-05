from typing import Union
from ant.devices import device_profiles
from ant.devices.common import DeviceType, Node


def auto_create_device(
    node: Node,
    device_id: int,
    device_type: Union[DeviceType, int, str],
    trans_type: int = 0,
):
    """
    Auto instantiates ANT+ device object based on supplied parameters

    :param node Node: USB ANT node
    :param device_id int: device ID or 0 for first found
    :param device_type Union[DeviceType, int, str]: device type as a DeviceType, device type int or DeviceType.name
    :param trans_type int: transmission type
    :raises ValueError: profile object for device does not exist - needs creating
    """
    if isinstance(device_type, int):
        dt = DeviceType(device_type)
    elif isinstance(device_type, str):
        dt = DeviceType[device_type]
    else:
        dt = device_type

    if dt in device_profiles:
        profile = device_profiles[dt]

        return profile(node, device_id=device_id, trans_type=trans_type)
    else:
        raise ValueError(f"{dt} not in device profiles {list(device_profiles.keys())}")
