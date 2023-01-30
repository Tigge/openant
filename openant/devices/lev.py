import logging
from dataclasses import dataclass, field
from enum import Enum

from ..easy.node import Node
from .common import AntPlusDevice, DeviceData, DeviceType

_logger = logging.getLogger(__name__)


class LevErrorMessage(Enum):
    NoError = 0
    BatteryError = 1
    DriveTrainError = 2
    BatteryEOL = 3
    Overheating = 4
    Unknown = 5  # 5-15 reserved
    ManufacturerSpecific = 16  # 16-255

    @classmethod
    def _missing_(cls, v):
        if v < 16:
            return LevErrorMessage.Unknown
        return LevErrorMessage.ManufacturerSpecific


class GearState(Enum):
    Automatic = 0
    Manual = 1
    Unknown = 2

    @classmethod
    def _missing_(cls, _):
        return GearState.Unknown


class TemperatureState(Enum):
    Unknown = 0
    Cold = 1
    ColdWarm = 2
    Warm = 3
    WarmHot = 4
    Hot = 5

    @classmethod
    def _missing_(cls, _):
        return TemperatureState.Unknown


class TemperatureAlert(Enum):
    NoAlert = 0
    Overheating = 1

    @classmethod
    def _missing_(cls, _):
        return TemperatureAlert.NoAlert


@dataclass
class LevData(DeviceData):
    """ANT+ light electric vehicle (LEV) data"""

    motor_temperature: TemperatureState = TemperatureState.Unknown
    motor_alert: TemperatureAlert = TemperatureAlert.NoAlert
    battery_temperature: TemperatureState = TemperatureState.Unknown
    battery_alert: TemperatureAlert = TemperatureAlert.NoAlert
    error_message: LevErrorMessage = LevErrorMessage.NoError
    speed: float = field(default=0.0, metadata={"unit": "km/h"})
    current_assist_level: int = 0
    current_regenerative_level: int = 0
    manual_throttle: bool = False
    lights: bool = False
    light_high_beam: bool = False
    turn_signal_left: bool = False
    turn_signal_right: bool = False
    gear_exist: bool = False
    gear_manual: bool = False
    gear_rear: int = 0
    gear_front: int = 0
    speed: float = field(default=0.0, metadata={"unit": "km/h"})
    odometer: float = field(default=0.0, metadata={"unit": "km"})
    remaining_range: int = field(default=0, metadata={"unit": "km"})
    fuel_consumption: float = field(default=0.0, metadata={"unit": "Wh/km"})
    assist: int = 0
    battery_soc: int = 0
    battery_cycles: int = 0
    battery_voltage: float = field(default=0.0, metadata={"unit": "V"})
    battery_distance_charge: float = field(default=0.0, metadata={"unit": "km"})
    wheel_circumference: int = field(default=0, metadata={"unit": "mm"})
    supported_assist_levels: int = 0
    supported_regenerative_levels: int = 0


@dataclass
class LevDisplayCommand(DeviceData):
    """ANT+ light electric vehicle (LEV) data"""

    gear_rear: int = 0
    gear_front: int = 0
    lights: bool = False
    light_high_beam: bool = False
    turn_signal_left: bool = False
    turn_signal_right: bool = False

    @staticmethod
    def to_int(dc):
        return (
            (dc.gear_rear << 6)
            | (dc.gear_front << 4)
            | (dc.lights << 3)
            | (dc.light_high_beam << 2)
            | (dc.turn_signal_left << 1)
            | (dc.turn_signal_right)
        )

    @staticmethod
    def to_bytes(dc):
        i = LevDisplayCommand.to_int(dc)
        return i.to_bytes(2, byteorder="little")


class Lev(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "lev",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.Lev.value,
            device_id=device_id,
            period=8192,
            name=name,
            trans_type=trans_type,
        )

        self.data = {**self.data, "lev": LevData()}

    def update_system_state(self, byte):
        self.data["lev"].manual_throttle = (byte & 0x10) == 0x10
        self.data["lev"].lights = (byte & 0x08) == 0x08
        self.data["lev"].light_high_beam = (byte & 0x04) == 0x04
        self.data["lev"].turn_signal_left = (byte & 0x02) == 0x02
        self.data["lev"].turn_signal_right = (byte & 0x01) == 0x01

    def update_travel_mode(self, byte):
        self.data["lev"].current_assist_level = (byte >> 3) & 0x07
        self.data["lev"].current_regenerative_level = byte & 0x07

    def update_gear_state(self, byte):
        self.data["lev"].gear_exist = (byte & 0x80) == 0x80
        self.data["lev"].gear_manual = (byte & 0x40) == 0x40
        self.data["lev"].gear_rear = (byte >> 2) & 0x07
        self.data["lev"].gear_front = byte & 0x03

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # main page
        if page == 0x01:
            self.data["lev"].motor_temperature = TemperatureState((data[1] >> 4) & 0x07)
            self.data["lev"].motor_alert = TemperatureAlert((data[1] >> 4) & 0x08)
            self.data["lev"].battery_temperature = TemperatureState(data[1] & 0x07)
            self.data["lev"].battery_alert = TemperatureAlert(data[1] & 0x08)
            # travel mode
            self.update_travel_mode(data[2])
            # system state
            self.update_system_state(data[3])
            # gear state
            self.update_gear_state(data[4])

            self.data["lev"].error_message = LevErrorMessage(data[5])
            # only first 4 bits of byte 7 for speed
            self.data["lev"].speed = (
                data[6] + ((data[7] & 0x0F) << 8)
            ) * 0.1  # 0.1 km/h units

            _logger.info(f"Lev {page} update {self}: {self.data['lev']}")
            self.on_device_data(page, "speed_system", self.data["lev"])
        # speed and distance
        elif page == 0x02:
            self.data["lev"].odometer = (
                int.from_bytes(data[1:4], byteorder="little") * 0.01
            )  # 0.01 km units
            self.data["lev"].remaining_range = data[4] + ((data[5] & 0x0F) << 8)
            self.data["lev"].speed = (
                data[6] + ((data[7] & 0x0F) << 8)
            ) * 0.1  # 0.1 km/h units

            _logger.info(f"Lev {page} update {self}: {self.data['lev']}")
            self.on_device_data(page, "speed_distance", self.data["lev"])
        # alternative speed and distance
        elif page == 0x22:
            self.data["lev"].odometer = (
                int.from_bytes(data[1:4], byteorder="little") * 0.01
            )  # 0.01 km units
            self.data["lev"].fuel_consumption = data[4] + ((data[5] & 0x0F) << 8) * 0.1
            self.data["lev"].speed = (
                data[6] + ((data[7] & 0x0F) << 8)
            ) * 0.1  # 0.1 km/h units

            _logger.info(f"Lev {page} update {self}: {self.data['lev']}")
            self.on_device_data(page, "alt_speed_distance", self.data["lev"])
        # system and speed 2
        elif page == 0x03:
            self.data["lev"].battery_soc = data[1] & 0x7F
            # travel mode
            self.update_travel_mode(data[2])
            # system state
            self.update_system_state(data[3])
            # gear state
            self.update_gear_state(data[4])

            self.data["lev"].assist = data[5]
            self.data["lev"].speed = (
                data[6] + ((data[7] & 0x0F) << 8)
            ) * 0.1  # 0.1 km/h units

            _logger.info(f"Lev {page} update {self}: {self.data['lev']}")
            self.on_device_data(page, "system_speed_2", self.data["lev"])
        # battery information
        elif page == 0x04:
            self.data["lev"].battery_cycles = data[2] + ((data[3] & 0x0F) << 8) * 0.1
            self.data["lev"].fuel_consumption = data[4] + ((data[3] & 0xF0) << 8) * 0.1
            self.data["lev"].battery_voltage = data[5] / 4
            self.data["lev"].battery_distance_charge = int.from_bytes(
                data[6:8], byteorder="little"
            )

            _logger.info(f"Lev {page} update {self}: {self.data['lev']}")
            self.on_device_data(page, "battery", self.data["lev"])
        # capabilities information
        elif page == 0x05:
            self.data["lev"].supported_assist_levels = (data[2] >> 3) & 0x07
            self.data["lev"].supported_regenerative_levels = data[2] & 0x07
            self.data["lev"].wheel_circumference = data[3] + ((data[4] & 0x0F) << 8)

            _logger.info(f"Lev {page} update {self}: {self.data['lev']}")
            self.on_device_data(page, "capabilities", self.data["lev"])

    def set_data(
        self,
        display_command=LevDisplayCommand,
        assist_level=0xFF,
        regenerative_level=0xFF,
        wheel_circumference=0xFF,
        manufacturer_id=0xFFFF,
    ):
        page = [0x00] * 8
        page[0] = 0x10
        page[1] = wheel_circumference & 0xFF
        page[2] = wheel_circumference & 0x0F
        if assist_level != 0xFF or regenerative_level != 0xFF:
            page[3] |= ((assist_level & 0x07) << 3) if assist_level != 0xFF else 0
            page[3] |= regenerative_level & 0x07 if regenerative_level != 0xFF else 0
        else:
            page[3] = 0xFF
        page[4:6] = LevDisplayCommand.to_bytes(display_command)
        page[6:8] = manufacturer_id.to_bytes(2, byteorder="little")

        self.channel.send_acknowledged_data(page)
