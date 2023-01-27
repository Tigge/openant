import dataclasses
import logging
import json
from typing import Tuple

from ..easy.node import Node
from .common import AntPlusDevice, CommonData, DeviceType
from .utilities import read_json

_logger = logging.getLogger(__name__)


class Scanner(AntPlusDevice):
    def __init__(
        self, node: Node, device_id=0, device_type=0, period=8070, trans_type=0
    ):
        super().__init__(
            node,
            device_type=device_type,
            device_id=device_id,
            period=period,
            trans_type=trans_type,
        )

        self.found = set()
        self.common = {}

    def _on_data(self, data):
        """Overloads _on_data for scanning of devices. Will not attach to single device but keep track of all devices found in the area."""

        # extended (> 8) has the device number and id beyond page
        if len(data) > 8:
            device_id = data[9] + (data[10] << 8)
            device_type = data[11]
            trans_type = data[12]
            tuple_device = (device_id, device_type, trans_type)

            if tuple_device not in self.found:
                info = {f"{device_id}:{device_type}": CommonData()}
                self.common.update(info)
                self.found.add(tuple_device)

                _logger.info(f"Found new device {info}")

                self.on_found(tuple_device)

            common = {}
            device_key = f"{device_id}:{device_type}"

            # manufacturer info
            if data[0] == 80:
                common["hardware_rev"] = data[3]
                common["manufacturer_id"] = data[4] + (data[5] << 8)
                common["model_no"] = data[6] + (data[7] << 8)

                # make an updated dataclass using current and new dict data
                updated = dataclasses.replace(self.common[device_key], **common)

                # only fire callback if the dataclass has changed
                if updated != self.common[device_key]:
                    self.common[device_key] = updated
                    _logger.info(
                        f"Manufacturer info {device_id}: HW Rev: {self.common[device_key].hardware_rev}; ID: {self.common[device_key].manufacturer_id}; Model: {self.common[device_key].model_no}"
                    )
                    self.on_update(tuple_device, self.common[device_key])
            # product info
            elif data[0] == 81:
                sw_rev = data[2]
                sw_main = data[3]

                if sw_rev == 0xFF:
                    common["software_ver"] = str(sw_main / 10)
                else:
                    common["software_ver"] = str((sw_main * 100 + sw_rev) / 1000)

                common["serial_no"] = int.from_bytes(data[4:8], byteorder="little")

                # make an updated dataclass using current and new dict data
                updated = dataclasses.replace(self.common[device_key], **common)

                # only fire callback if the dataclass has changed
                if updated != self.common[device_key]:
                    self.common[device_key] = updated
                    _logger.info(
                        f"Product info {device_id}: Software: {updated.software_ver}; Serial Number: {updated.serial_no}"
                    )
                    self.on_update(tuple_device, self.common[device_key])

    def save(self, file_path: str):
        """
        Save the devices found in session to a file_path in json format

        :param file_path str: path to .json file to save
        """
        jdata = read_json(file_path)

        if jdata:
            devices = jdata["devices"]
            existing = set(dev["id"] for dev in devices)
        else:
            jdata = {}
            devices = []
            existing = set()

        for dev in self.found:
            device_id, device_type, device_trans = dev
            device_key = f"{device_id}:{device_type}"

            if device_id not in existing:
                devices.append(
                    {
                        "device": str(DeviceType(device_type).name),
                        "id": device_id,
                        "type": device_type,
                        "transmission_type": device_trans,
                        "serial": self.common[device_key].serial_no,
                    }
                )

        jdata["devices"] = devices

        with open(file_path, "w") as fh:
            json.dump(jdata, fh, indent=4, sort_keys=True)

    @staticmethod
    def on_found(device_tuple: Tuple[int, int, int]):
        """
        Callback when a new device is found

        :param _ Tuple[int, int, int]: (device_id, device_type, transmission_type) of found device
        """
        assert device_tuple  # type: ignore
        pass

    @staticmethod
    def on_update(device_tuple: Tuple[int, int, int], common: CommonData):
        """
        Callback when a device updates it's common date pages

        :param dev Tuple[int, int, int]: (device_id, device_type, transmission_type) of found device
        :param common CommonData: common page data of device
        """
        assert device_tuple  # type: ignore
        assert common
        pass
