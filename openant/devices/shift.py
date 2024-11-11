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

class FunctionSetEventType(Enum):
    Single = 0
    Double = 1
    Long = 2
    System = 3
    Unknown = 4

    @classmethod
    def _missing_(cls, _):
        return FunctionSetEventType.Unknown


@dataclass
class FunctionSetEvent:
    function_set_id: int = field(default=0)
    function_set_event_type: FunctionSetEventType = field(default=FunctionSetEventType.Unknown)

@dataclass
class FunctionSetConfiguration:
    is_short_press_enabled: bool = field(default=False)
    is_double_press_enabled: bool = field(default=False)
    is_long_press_enabled: bool = field(default=False)


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
    function_set_1_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_2_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_3_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_4_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_5_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_6_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_7_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    function_set_8_configuration: FunctionSetConfiguration = field(default_factory=FunctionSetConfiguration())
    event_count: int = field(default=0)
    event_1: FunctionSetEvent = field(default_factory=FunctionSetEvent())
    event_2: FunctionSetEvent = field(default_factory=FunctionSetEvent())
    event_3: FunctionSetEvent = field(default_factory=FunctionSetEvent())
    event_4: FunctionSetEvent = field(default_factory=FunctionSetEvent())
    event_5: FunctionSetEvent = field(default_factory=FunctionSetEvent())
    event_6: FunctionSetEvent = field(default_factory=FunctionSetEvent())
    max_trim_rear: int = field(default=0)
    max_trim_front: int = field(default=0)
    current_trim_rear: int = field(default=0)
    current_trim_front: int = field(default=0)


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

        self._event_count = [[0, 0], [0, 0], [0,0]] # For pages 0x01, 0x02, 0x04

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
            self._event_count[0][0] = self._event_count[0][1]
            self._event_count[0][1] = data[1]

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
                self._event_count[0][1] + 256 - self._event_count[0][0]
            ) % 256

            # if it's a new event (count change)
            if delta_update_count:
                _logger.info(f"Shifting status update {self}: {self.data['shift']}")
                self.on_device_data(page, "shift_system_status", self.data["shift"])
        elif page == 0x02:
            self._event_count[1][0] = self._event_count[1][1]
            self._event_count[1][1] = data[1]

            self.data["shift"].event_count = data[1]

            self.data["shift"].event_1 = FunctionSetEvent(data[2] & 0x0F, FunctionSetEventType((data[2] & 0x03) >> 4))
            self.data["shift"].event_2 = FunctionSetEvent(data[3] & 0x0F, FunctionSetEventType((data[3] & 0x03) >> 4))
            self.data["shift"].event_3 = FunctionSetEvent(data[4] & 0x0F, FunctionSetEventType((data[4] & 0x03) >> 4))
            self.data["shift"].event_4 = FunctionSetEvent(data[5] & 0x0F, FunctionSetEventType((data[5] & 0x03) >> 4))
            self.data["shift"].event_5 = FunctionSetEvent(data[6] & 0x0F, FunctionSetEventType((data[6] & 0x03) >> 4))

            delta_update_count = (
                self._event_count[1][1] + 256 - self._event_count[1][0]
            ) % 256

            # if it's a new event (count change)
            if delta_update_count:
                _logger.info(f"Shifting status update {self}: {self.data['shift']}")
                self.on_device_data(page, "shift_system_status", self.data["shift"])
        elif page == 0x03:
            self.data["shift"].function_set_1_configuration = FunctionSetConfiguration(bool(data[1] & 0x02), bool(data[1] & 0x04), bool(data[1] & 0x08))
            self.data["shift"].function_set_2_configuration = FunctionSetConfiguration(bool(data[2] & 0x02), bool(data[2] & 0x04), bool(data[2] & 0x08))
            self.data["shift"].function_set_3_configuration = FunctionSetConfiguration(bool(data[3] & 0x02), bool(data[3] & 0x04), bool(data[3] & 0x08))
            self.data["shift"].function_set_4_configuration = FunctionSetConfiguration(bool(data[4] & 0x02), bool(data[4] & 0x04), bool(data[4] & 0x08))
            self.data["shift"].function_set_5_configuration = FunctionSetConfiguration(bool(data[5] & 0x02), bool(data[5] & 0x04), bool(data[5] & 0x08))
            self.data["shift"].function_set_6_configuration = FunctionSetConfiguration(bool(data[6] & 0x02), bool(data[6] & 0x04), bool(data[6] & 0x08))
            self.data["shift"].function_set_7_configuration = FunctionSetConfiguration(bool(data[7] & 0x02), bool(data[7] & 0x04), bool(data[7] & 0x08))
            self.data["shift"].function_set_8_configuration = FunctionSetConfiguration(bool(data[8] & 0x02), bool(data[8] & 0x04), bool(data[8] & 0x08))

        elif page == 0x04:
            self._event_count[2][0] = self._event_count[2][1]
            self._event_count[2][1] = data[1]

            self.data["shift"] = ShiftData()

            self.data["shift"].max_trim_rear = data[2]
            self.data["shift"].max_trim_front = data[3]
            self.data["shift"].current_trim_rear = data[4]
            self.data["shift"].current_trim_front = data[5]

            delta_update_count = (
                self._event_count[2][1] + 16 - self._event_count[2][0]
            ) % 16

            # if it's a new event (count change)
            if delta_update_count:
                _logger.info(f"Shifting status update {self}: {self.data['shift']}")
                self.on_device_data(page, "shift_system_status", self.data["shift"])
            pass