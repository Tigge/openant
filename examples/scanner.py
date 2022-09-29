from ant.easy.node import Node

from ant.devices.common import DeviceType
from ant.devices.scanner import Scanner

# standard ANT+ network key
NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]

def on_found(device_tuple):
    device_id, device_type, device_trans = device_tuple
    print(f"Found new device #{device_id} {DeviceType(device_type)}; device_type: {device_type}, transmission_type: {device_trans}")

def on_update(device_tuple, common):
    device_id = device_tuple[0]
    print(f"Device #{device_id} commond data update: {common}")

def main(file_path=None):
    node = Node()
    node.set_network_key(0x00, NETWORK_KEY)

    scanner = Scanner(node)

    scanner.on_found = on_found
    scanner.on_update = on_update

    try:
        print(f"Starting scanner, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print(f"Closing ANT+ node...")
    finally:
        scanner.close_channel()
        if file_path:
            print(f"Saving/updating found devices to {file_path}")
            scanner.save(file_path)
        node.stop()

if __name__ == "__main__":
    main()
