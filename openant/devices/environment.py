"""
ANT+ environment temperature device profile
"""
import logging
from dataclasses import dataclass, field

from .common import DeviceData, AntPlusDevice, DeviceType, BatteryStatus
from ..easy.node import Node

_logger = logging.getLogger(__name__)


@dataclass
class EnvironmentData(DeviceData):
    """ANT+ environment data."""

    temperature: float = field(default=-1, metadata={"unit": "C"})
    min_24h_temperature: float = field(default=-1, metadata={"unit": "C"})
    max_24h_temperature: float = field(default=-1, metadata={"unit": "C"})


class Environment(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "environment",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.Environment.value,
            device_id=device_id,
            period=8070,
            name=name,
            trans_type=trans_type,
        )

        self.data = {**self.data, "environment": EnvironmentData()}

    def on_data(self, data):
        page = data[0]
        _logger.debug(f"{self} on_data: {data}")

        if page == 1:
            # Data page 1, temperature info
            # bytes 6,7 indicate temperature, LSB first
            low_msn = (data[4] & 0xF0)>>4
            high_lsn = (data[4] & 0x0F)<<4
            self.data["environment"].temperature = (
                int.from_bytes(data[6:8], byteorder="little") * 0.01
            )
            self.data["environment"].min_24h_temperature = (
                int.from_bytes([data[3], low_msn], byteorder="little") * 0.1
            )
            self.data["environment"].max_24h_temperature = (
                (int.from_bytes([data[5],high_lsn], byteorder="big")>>4) * 0.1
            )

            self.on_device_data(page, "environment", self.data["environment"])
