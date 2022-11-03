"""
ANT+ heart rate monitor device profile
"""
import logging

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import DeviceData, AntPlusDevice, DeviceType, BatteryStatus

_logger = logging.getLogger(__name__)


@dataclass
class HeartRateData(DeviceData):
    """ANT+ heart rate data (tpms)."""

    page_specific: int = 0xFFFFFF
    beat_time: float = -1
    beat_count: int = 0
    heart_rate: int = field(default=0, metadata={"unit": "bpm"})
    operating_time: int = 0xFFFFFF
    manufacturer_id_lsb: int = 0xFF
    serial_number: int = 0xFFFF
    previous_heart_beat_time: float = -1
    battery_percentage: int = 0xFF


class HeartRate(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "heart_rate",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.HeartRate.value,
            device_id=device_id,
            period=8070,
            name=name,
            trans_type=trans_type,
        )

        self._event_count = [0, 0]

        self.data = {**self.data, "heart_rate": HeartRateData()}

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # MSB is page change toggle, 0-7 can be rotated with page specific data but all include these bytes
        if (page & 0x0F) <= 7:
            self._event_count[0] = self._event_count[1]
            self._event_count[1] = data[6]
            dp = page & 0x0F

            self.data["heart_rate"].page_specific = int.from_bytes(
                data[1:4], byteorder="little"
            )
            self.data["heart_rate"].beat_time = (
                int.from_bytes(data[4:6], byteorder="little") / 1024
            )
            self.data["heart_rate"].beat_count = data[6]
            self.data["heart_rate"].heart_rate = data[7]

            if dp == 0x01:
                self.data["heart_rate"].operating_time = (
                    self.data["heart_rate"].page_specific * 2
                )
            elif dp == 0x02:
                self.data["heart_rate"].manufacturer_id_lsb = data[1]
                self.data["heart_rate"].serial_number = int.from_bytes(
                    data[2:4], byteorder="little"
                )
            # background page product info
            elif dp == 0x03:
                pass
            # main page previous heart beat
            elif dp == 0x04:
                self.data["heart_rate"].previous_heart_beat_time = (
                    int.from_bytes(data[2:4], byteorder="little") / 1024
                )
            # swim interval stuff
            elif dp == 0x05:
                pass
            elif dp == 0x06:
                self.data["heart_rate"].features_supported = data[2]
                self.data["heart_rate"].features_enabled = data[3]
            elif dp == 0x07:
                self.data["heart_rate"].battery_percentage = data[1]
                self.data["common"].last_battery_data.voltage_fractional = data[2] / 256
                self.data["common"].last_battery_data.voltage_coarse = data[3] & 0x0F
                self.data["common"].last_battery_data.status = BatteryStatus(
                    (data[3] & 0x70) >> 4
                )
                # trigger the on battery callback
                self._on_battery(self.data["common"].last_battery_data)

            self.on_device_data(page, "heart_rate", self.data["heart_rate"])
