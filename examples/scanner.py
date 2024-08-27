from openant.easy.node import Node

from openant.devices.common import DeviceType
from openant.devices.scanner import Scanner
from openant.devices.utilities import auto_create_device
from openant.devices import ANTPLUS_NETWORK_KEY

# also see `auto_scanner` in ant/subparsers/scan.py
def example_scan(file_path=None, device_id=0, device_type=0, auto_create=False):
    # list of auto created devices
    devices = []

    # ANT USB node
    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

    # the scanner
    scanner = Scanner(node, device_id=device_id, device_type=device_type)

    # local function to call when device updates common data
    def on_update(device_tuple, common):
        device_id = device_tuple[0]
        print(f"Device #{device_id} common data update: {common}")

    # local function to call when device update device speific page data
    def on_device_data(device, page_name, data):
        print(f"Device {device} broadcast {page_name} data: {data}")

    # local function to call when a device is found - also does the auto-create if enabled
    def on_found(device_tuple):
        device_id, device_type, device_trans = device_tuple
        print(
            f"Found new device #{device_id} {DeviceType(device_type)}; device_type: {device_type}, transmission_type: {device_trans}"
        )

        if auto_create and len(devices) < 16:
            try:
                dev = auto_create_device(node, device_id, device_type, device_trans)
                # closure callback of on_device_data with device
                dev.on_device_data = lambda _, page_name, data, dev=dev: on_device_data(
                    dev, page_name, data
                )
                devices.append(dev)
            except Exception as e:
                print(f"Could not auto create device: {e}")

    # add callback functions to scanner
    scanner.on_found = on_found
    scanner.on_update = on_update

    # start scanner, exit on keyboard and clean up USB device on exit
    try:
        print(
            f"Starting scanner for #{device_id}, type {device_type}, press Ctrl-C to finish"
        )
        node.start()
    except KeyboardInterrupt:
        print("Closing ANT+ node...")
    finally:
        scanner.close_channel()
        if file_path:
            print(f"Saving/updating found devices to {file_path}")
            scanner.save(file_path)

        for dev in devices:
            dev.close_channel()

        node.stop()


if __name__ == "__main__":
    example_scan()
