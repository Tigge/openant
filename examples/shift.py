from ant.devices.common import BatteryData
from ant.easy.node import Node
from ant.devices.shift import Shifting, ShiftData, ShiftingSystemID

# standard ANT+ network key
NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]

def main(device_id=0):
    node = Node()
    node.set_network_key(0x00, NETWORK_KEY)

    device = Shifting(node, device_id=device_id)

    def on_found():
        print(f"Device {device} found and receiving")

    def on_device_data(page: int, page_name: str, data):
        if isinstance(data, ShiftData):
            if data.total_front > 1:
                print(f"Rear gear: {data.gear_rear + 1}/{data.total_rear}; Front gear: {data.gear_front + 1}/{data.total_front}")
            else:
                print(f"Rear gear: {data.gear_rear + 1}/{data.total_rear}")

    def on_battery(data: BatteryData):
        if data.battery_id != 0xFF:
            battery_id = ShiftingSystemID(data.battery_id)
            print(f"{battery_id.name} battery {data.voltage_coarse + data.voltage_fractional} V, operating time {data.operating_time} seconds")

    device.on_found = on_found
    device.on_device_data = on_device_data
    device.on_battery = on_battery

    try:
        print(f"Starting {device}, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print(f"Closing ANT+ device...")
    finally:
        device.close_channel()
        node.stop()

if __name__ == "__main__":
    main()
