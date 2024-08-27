import os
import uuid
from typing import List, Optional

from ..easy.node import Node

from ..devices import device_profiles, ANTPLUS_NETWORK_KEY
from ..devices.utilities import auto_create_device, read_json
from ..devices.common import DeviceData, AntPlusDevice
from ..devices.fitness_equipment import FitnessEquipment, Workout

import influxdb_client as idb
from influxdb_client.client.write_api import SYNCHRONOUS


def write_device_data_influx(
    data: DeviceData,
    client: idb.InfluxDBClient,
    bucket: str,
    wuuid: str,
    device_name: str,
    verbose=True,
):
    host = os.uname().nodename

    if not data:
        raise ValueError("Device has no data")

    try:
        influx_tags = {
            "device": device_name,
            "uuid": wuuid,
            "host": host,
        }

        json = data.to_influx_json(tags=influx_tags)

        if verbose:
            print(f"Writing: {json}")

        point = point = idb.Point.from_dict(json)

        with client.write_api(write_options=SYNCHRONOUS) as c:
            c.write(bucket=bucket, record=point)

    except Exception as e:
        print(f"Exception during influx write: {e}")


def write_all_device_data_influx(
    device: AntPlusDevice,
    client: idb.InfluxDBClient,
    bucket: str,
    wuuid: str,
    verbose=True,
):
    host = os.uname().nodename

    try:
        influx_tags = {
            "device": str(device),
            "serial_no": device.data["common"].serial_no,
            "uuid": wuuid,
            "host": host,
        }

        # drop common since it's just const meta
        data = device.data.copy()
        data.pop("common")

        json = [v.to_influx_json(tags=influx_tags) for v in data.values()]

        if verbose:
            print(f"Writing: {json}")

        with client.write_api(write_options=SYNCHRONOUS) as c:
            for j in json:
                point = point = idb.Point.from_dict(j)
                c.write(bucket=bucket, record=point)

    except Exception as e:
        print(f"Exception during influx write: {e}")


def device_data_influx_importer(
    node: Node,
    client: idb.InfluxDBClient,
    bucket: str,
    devices: List[AntPlusDevice],
    session_uuid: str = str(uuid.uuid4()),
    verbose: bool = False,
    workouts: Optional[List[Workout]] = None,
):
    print(f"Starting device data importer UUID {session_uuid} for {devices}")

    # method with args saved to pass to device page update callback - could pass args list with callback instead if this gets messsy...
    def write_device_data(device, page_name, data):
        print(f"Device {device} broadcast {page_name} data: {data}")
        write_device_data_influx(
            data,
            client,
            bucket=bucket,
            wuuid=session_uuid,
            device_name=str(device),
            verbose=verbose,
        )

    def on_found(device):
        print(f"Device {device} found and receiving")

        if type(device) == FitnessEquipment:
            if workouts is not None:
                device.start_workouts(workouts)

    for dev in devices:
        dev.on_found = lambda dev=dev: on_found(dev)
        dev.on_device_data = lambda page, page_name, data, dev=dev: write_device_data(
            dev, page_name, data
        )

    try:
        print(f"Starting {devices}, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print(f"Closing ANT+ devices...")
    finally:
        for dev in devices:
            dev.close_channel()

        node.stop()
        client.close()


def _run(args):
    # create influx connection
    client = idb.InfluxDBClient(url=args.url, token=args.token, org=args.org)

    if args.verbose:
        print(f"Created InfluxDB {client}")

    # ping client now before stream
    client.ping()

    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

    devices = []
    workouts = None

    # load from config file if config
    if args.device == "config":
        if args.config:
            config = read_json(args.config)

            if config:
                # bit dirty but initialises classes based on snake_case string provided - TODO change when imported from module
                for dev in config["devices"]:
                    try:
                        class_name = dev["device"]
                        device_id = dev["id"]
                        trans_type = dev["transmission_type"]
                        devices.append(
                            auto_create_device(
                                node,
                                device_id=device_id,
                                device_type=class_name,
                                trans_type=trans_type,
                            )
                        )
                    except Exception as e:
                        raise ValueError(
                            f"Failed to create device {dev} from {args.config} - is it a valid AntPlusDevice?"
                        )

                if "workouts" in config:
                    try:
                        workouts = [
                            Workout.from_arrays(
                                x["powers"],
                                x["periods"],
                                cycles=x["cycles"],
                                loop=x["loop"],
                            )
                            if x["type"] == "arrays"
                            else Workout.from_ramp(
                                start=x["start"],
                                stop=x["stop"],
                                step=x["step"],
                                period=x["period"],
                                peak=(x["peak"] if "peak" in x else None),
                                cycles=x["cycles"],
                                loop=x["loop"],
                            )
                            for x in config["workouts"]
                        ]
                    except Exception as e:
                        print(f"Failed to parse workouts in {args.config}: {e}")

            else:
                raise ValueError("Invalid or missing config file")
        else:
            raise ValueError(
                "--config arg with path to .json device configuation must be supplied!"
            )
    # else create DeviceType class
    else:
        devices.append(
            auto_create_device(
                node,
                device_id=args.id,
                device_type=args.device,
                trans_type=args.transtype,
            )
        )

    device_data_influx_importer(
        node=node,
        client=client,
        bucket=args.bucket,
        devices=devices,
        verbose=args.verbose,
        workouts=workouts,
    )


def add_subparser(subparsers, name="influx"):
    antinflux = subparsers.add_parser(
        name,
        description=("Capture DeviceData from an ANT+ device and import to InfluxDB"),
    )
    antinflux.add_argument(
        "device",
        choices=list(device_profiles.keys()).append("config"),
        help=f"Device {list(device_profiles.keys())} to use or 'config' for --config flag file",
    )
    antinflux.add_argument(
        "--config",
        type=str,
        help=".json config file for use with 'config' type",
    )
    antinflux.add_argument(
        "--url",
        default="http://localhost:8086",
        type=str,
        help="URL for InfluxDB server",
    )
    antinflux.add_argument(
        "--token",
        type=str,
        help="port of InfluxDB server",
    )
    antinflux.add_argument(
        "--org",
        default="my-org",
        type=str,
        help="organisation to use on InfluxDB server",
    )
    antinflux.add_argument(
        "--bucket",
        type=str,
        default="my-bucket",
        help="influxDB bucket to write to",
    )
    antinflux.add_argument(
        "-I",
        "--id",
        type=int,
        default=0,
        help="Device ID, default zero will attach to first found",
    )
    antinflux.add_argument(
        "-T",
        "--transtype",
        type=int,
        default=0,
        help="Transmission type, default zero will attach to first found",
    )
    antinflux.add_argument(
        "-V", "--verbose", action="store_true", help="verbose output"
    )
    antinflux.set_defaults(func=_run)
