from openant.easy.node import Node
from openant.devices import ANTPLUS_NETWORK_KEY
from openant.devices.tire_pressure_monitor import TirePressureMonitor, TirePressureData


def main(device_id=0):
    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

    tpms = TirePressureMonitor(node, device_id=device_id)

    def on_found():
        print(f"Device {tpms} found and receiving")

    def on_device_data(page: int, page_name: str, data):
        if page_name == "tire_pressure" and isinstance(data, TirePressureData):
            print(
                f"Tire {data.position} pressure: {data.pressure} mB; {data.pressure * 0.1} kPa; {data.pressure / 68.947573} psi"
            )

    tpms.on_found = on_found
    tpms.on_device_data = on_device_data

    try:
        print(f"Starting {tpms}, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print(f"Closing ANT+ device...")
    finally:
        tpms.close_channel()
        node.stop()


if __name__ == "__main__":
    main()
