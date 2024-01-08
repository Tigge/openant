import logging
from enum import Enum
from typing import List, Optional

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import DeviceData, AntPlusDevice, DeviceType, BatteryStatus

_logger = logging.getLogger(__name__)


class CoreTempDataQuality(Enum):
    Poor = 0
    Fair = 1
    Good = 2
    Excelent = 3

    Unused = 0xFF

    @classmethod
    def _missing_(cls, _):
        return PressureSensorAlarm.Unknown


@dataclass
class CoteTemperatureData(DeviceData):
    """ANT+ core temp data"""

    quality: CoreTempDataQuality = None
    skin_temp: float = field(default=0, metadata={"unit": "°C"})
    core_temp: float = field(default=0, metadata={"unit": "°C"})


class CoreTemperature(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "core_temp",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.CoreTemp.value,
            device_id=device_id,
            period=16384,  # 2Hz
            name=name,
            trans_type=trans_type,
        )

        self._event_count = [0, 0]

        self.data = {**self.data, "core_temp": CoteTemperatureData()}

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # General info
        if page == 0x00:
            self.data["core_temp"].quality = CoreTempDataQuality(data[2])

        # core temp main page
        elif page == 0x01:
            self._event_cout = data[1]
            self.data["core_temp"].skin_temp = (
                data[3] | ((data[4] & 0xF0) << 4)
            ) * 0.05
            self.data["core_temp"].core_temp = (
                int.from_bytes(data[6:8], byteorder="little") * 0.01
            )

        self.on_device_data(page, "core_temp", self.data["core_temp"])
