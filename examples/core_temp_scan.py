import sys
sys.path.append("..") 

from openant.easy.node import Node
from openant.devices import ANTPLUS_NETWORK_KEY
from openant.devices.core_temp import CoreTemperature, CoteTemperatureData


def main(device_id=0):
    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

    device = CoreTemperature(node, device_id=device_id)

    def on_found():
        print(f"Device {device} found and receiving")

    def on_device_data(page: int, page_name: str, data):
        # if isinstance(data, CoteTemperatureData):
        print(f"Data: ", data)

    device.on_found = on_found
    device.on_device_data = on_device_data

    try:
        print(f"Starting {device}, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print("Closing ANT+ device...")
    finally:
        device.close_channel()
        node.stop()


if __name__ == "__main__":
    main()
