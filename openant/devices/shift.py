import logging
from enum import Enum

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import BatteryData, DeviceData, AntPlusDevice, DeviceType

_logger = logging.getLogger(__name__)


class ShiftingSystemID(Enum):
    System = 0
    FrontDerailleur = 1
    RearDerailleur = 2
    LeftShifter = 3
    RightShifter = 4
    Shifter = 5
    LeftExtensionShifter = 6
    RightExtensionShifter = 7
    ExtensionShifter1 = 8
    LeftExtensionShifter2 = 9
    RightExtensionShifter2 = 10
    ExtensionShifter2 = 11
    Unknown = 15

    @classmethod
    def _missing_(cls, _):
        return ShiftingSystemID.Unknown


@dataclass
class ShiftData(DeviceData):
    """ANT+ shifting data (shift)"""

    gear_rear: int = field(default=31)
    gear_front: int = field(default=7)
    total_rear: int = field(default=0)
    total_front: int = field(default=0)
    invalid_inboard_rear: int = field(default=0)
    invalid_outboard_rear: int = field(default=0)
    invalid_inboard_front: int = field(default=0)
    invalid_outboard_front: int = field(default=0)
    shift_failure_rear: int = field(default=0)
    shift_failure_front: int = field(default=0)


class Shifting(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "shifting",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.Shifting.value,
            device_id=device_id,
            period=8192,
            name=name,
            trans_type=trans_type,
        )

        self._event_count = [0, 0]

        self.data = {**self.data, "shift": ShiftData()}

    def _on_battery(self, data: BatteryData):
        if data.battery_id != 0xFF:
            battery_id = ShiftingSystemID(data.battery_id)
            _logger.info(f"Shifting {battery_id.name} battery update {data}")
        else:
            _logger.info(
                f"Battery info {self}: ID: {self.data['common'].last_battery_id}; Fractional V: {self.data['common'].last_battery_data.voltage_fractional} V; Coarse V: {self.data['common'].last_battery_data.voltage_coarse} V; Status: {self.data['common'].last_battery_data.status}"
            )

        self.on_battery(data)

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # main page
        if page == 0x01:
            self._event_count[0] = self._event_count[1]
            self._event_count[1] = data[1]

            self.data["shift"].gear_rear = data[3] & 0x1F
            self.data["shift"].gear_front = (data[3] & 0xE0) >> 5
            self.data["shift"].total_rear = data[4] & 0x1F
            self.data["shift"].total_front = (data[4] & 0xE0) >> 5
            self.data["shift"].invalid_inboard_rear = data[5] & 0x0F
            self.data["shift"].invalid_outboard_rear = (data[5] & 0xF0) >> 4
            self.data["shift"].invalid_inboard_front = data[6] & 0x0F
            self.data["shift"].invalid_outboard_front = (data[6] & 0xF0) >> 4
            self.data["shift"].shift_failure_rear = data[7] & 0x0F
            self.data["shift"].shift_failure_front = (data[7] & 0xF0) >> 4

            delta_update_count = (
                self._event_count[1] + 256 - self._event_count[0]
            ) % 256

            # if it's a new event (count change)
            if delta_update_count:
                _logger.info(f"Shifting status update {self}: {self.data['shift']}")
                self.on_device_data(page, "shift_system_status", self.data["shift"])
