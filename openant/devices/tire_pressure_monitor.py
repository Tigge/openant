import logging
from enum import Enum

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import DeviceData, AntPlusDevice, DeviceType

_logger = logging.getLogger(__name__)


class PressureSensorPosition(Enum):
    Front = 1
    Rear = 2
    Unknown = 0

    @classmethod
    def _missing_(cls, _):
        return PressureSensorPosition.Unknown


class PressureSensorAlarm(Enum):
    AllWell = 0
    HighPressure = 1
    LowPressure = 2
    Unknown = 0xFF

    @classmethod
    def _missing_(cls, _):
        return PressureSensorAlarm.Unknown


@dataclass
class TirePressureData(DeviceData):
    """
    ANT+ tire pressure monitor data (tpms)
    """

    position: PressureSensorPosition = field(default=PressureSensorPosition.Unknown)
    alarm_state: PressureSensorAlarm = field(default=PressureSensorAlarm.Unknown)
    capabilities: int = field(default=0)
    pressure: int = field(default=0x8000, metadata={"unit": "Millibar"})
    barometric_pressure: int = field(default=0x8000, metadata={"unit": "Millibar"})
    low_pressure_alarm: int = field(default=0x8000, metadata={"unit": "Millibar"})
    high_pressure_alarm: int = field(default=0x8000, metadata={"unit": "Millibar"})


class TirePressureMonitor(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "tire_pressure_monitor",
        trans_type: int = 0,
    ):
        # device 48 so make ANT+ device with that device type, period switches between 4 Hz (8192) when pumping and 1 Hz (32768) during normal use
        super().__init__(
            node,
            device_type=DeviceType.TirePressureMonitor.value,
            device_id=device_id,
            period=8192,
            name=name,
            trans_type=trans_type,
        )

        self.data = {**self.data, "tpms": TirePressureData()}

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # main page
        if page == 0x01:
            self.data["tpms"].position = PressureSensorPosition(data[1] & 0x0F)
            self.data["tpms"].alarm_state = PressureSensorAlarm((data[1] & 0xF0) >> 4)
            self.data["tpms"].capabilities = data[2]

            self.data["tpms"].pressure = int.from_bytes(data[6:8], byteorder="little")

            _logger.info(f"Tire pressure main update {self}: {self.data['tpms']}")

            self.on_device_data(page, "tire_pressure", self.data["tpms"])
        # get/set parameters
        if page == 0x10:
            self.data["tpms"].position = PressureSensorPosition(data[1] & 0x0F)
            self.data["tpms"].alarm_state = PressureSensorAlarm((data[1] & 0xF0) >> 4)
            self.data["tpms"].barometric_pressure = int.from_bytes(
                data[2:4], byteorder="little"
            )
            self.data["tpms"].low_pressure_alarm = int.from_bytes(
                data[4:6], byteorder="little"
            )
            self.data["tpms"].high_pressure_alarm = int.from_bytes(
                data[6:8], byteorder="little"
            )

            self.on_device_data(page, "get_set", self.data["tpms"])

    def set_data(
        self,
        data: TirePressureData,
        set_position=False,
        set_barametric=False,
        set_high_pressure=False,
        set_low_pressure=False,
    ):
        page = [0x00] * 8
        page[0] = 0x10
        page[1] = data.position.value | (
            (
                set_position
                | set_barametric << 1
                | set_high_pressure << 2
                | set_low_pressure << 3
            )
            << 4
        )
        page[2] = data.barometric_pressure & 0xFF
        page[3] = (data.barometric_pressure >> 8) & 0xFF
        page[4] = data.low_pressure_alarm & 0xFF
        page[5] = (data.low_pressure_alarm >> 8) & 0xFF
        page[6] = data.high_pressure_alarm & 0xFF
        page[7] = (data.high_pressure_alarm >> 8) & 0xFF

        self.channel.send_acknowledged_data(page)
