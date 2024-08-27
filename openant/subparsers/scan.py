from ..easy.node import Node
from ..devices import ANTPLUS_NETWORK_KEY
from ..devices.common import DeviceType
from ..devices.scanner import Scanner
from ..devices.utilities import auto_create_device


def auto_scanner(file_path=None, device_id=0, device_type=0, auto_create=False):
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
        print(f"Device #{device_id} commond data update: {common}")

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
        print(f"Closing ANT+ node...")
    finally:
        scanner.close_channel()
        if file_path:
            print(f"Saving/updating found devices to {file_path}")
            scanner.save(file_path)

        for dev in devices:
            dev.close_channel()

        node.stop()


def _run(args):
    if args.device_type == DeviceType.Unknown.name:
        device_type = 0
    else:
        device_type = DeviceType[args.device_type].value

    auto_scanner(
        file_path=args.outfile,
        device_id=args.device_id,
        device_type=device_type,
        auto_create=args.auto_create,
    )


def add_subparser(subparsers, name="scan"):
    parser = subparsers.add_parser(
        name=name,
        description="Scan for ANT+ devices and print information to terminal/save to file",
    )
    parser.add_argument(
        "--logging",
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--outfile",
        "-o",
        type=str,
        help=".json file to save found device info",
    )
    parser.add_argument(
        "--device_type",
        "-t",
        type=str,
        default=DeviceType.Unknown.name,
        choices=[x.name for x in DeviceType],
        help="Device type to scan for, default Unknown is all",
    )
    parser.add_argument(
        "--device_id",
        "-i",
        type=int,
        default=0,
        help="Device ID to scan for, default 0 is all",
    )
    parser.add_argument(
        "--auto_create",
        "-a",
        action="store_true",
        help="Auto-create device profile object and print device page data updates",
    )

    parser.set_defaults(func=_run)
