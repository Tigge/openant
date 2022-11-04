from openant.easy.node import Node
from openant.devices import ANTPLUS_NETWORK_KEY
from openant.devices.bike_speed_cadence import (
    BikeSpeed,
    BikeCadence,
    BikeSpeedCadence,
    BikeSpeedData,
    BikeCadenceData,
)

WHEEL_CIRCUMFERENCE_M = 2.3


def main(device_id=0):
    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

    # device = BikeSpeed(node, device_id=device_id)
    # device = BikeCadence(node, device_id=device_id)
    device = BikeSpeedCadence(node, device_id=device_id)

    def on_found():
        print(f"Device {device} found and receiving")

    def on_device_data(page: int, page_name: str, data):
        if isinstance(data, BikeCadenceData):
            cadence = data.cadence
            if cadence:
                print(f"cadence: {cadence:.2f} rpm")
        elif isinstance(data, BikeSpeedData):
            speed = data.calculate_speed(WHEEL_CIRCUMFERENCE_M)
            if speed:
                print(f"speed: {speed:.2f} km/h")

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
