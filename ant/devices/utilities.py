from typing import Union
from . import device_profiles
from . common import DeviceType, Node

def auto_create_device(node: Node, device_id: int, device_type: Union[DeviceType, int, str], trans_type=0):
    if isinstance(device_type, DeviceType):
        dt = device_type
    elif isinstance(device_type, str):
        dt = DeviceType[device_type]
    else:
        dt = DeviceType(device_type)

    if dt in device_profiles:
        profile = device_profiles[dt]

        return profile(
            node, device_id=device_id, trans_type=trans_type
        )
    else:
        raise ValueError(f"{dt} is not in {list(device_profiles.keys())}")
