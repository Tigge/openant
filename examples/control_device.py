import logging
from openant.devices import ANTPLUS_NETWORK_KEY
from openant.easy.node import Node
from openant.devices.controls_device import (
    GenericControllableDevice,
    ControlCommand,
)


def main(device_id=1):
    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

    device = GenericControllableDevice(node, device_id=device_id)

    def on_control_command(command: ControlCommand, raw: int):
        print(f"Control command: {command}")

    device.on_control_command = on_control_command

    try:
        print(f"Starting {device}, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print(f"Closing ANT+ device...")
    finally:
        device.close_channel()
        node.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
