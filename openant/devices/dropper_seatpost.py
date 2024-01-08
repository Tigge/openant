import logging
from enum import Enum

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import BatteryData, DeviceData, AntPlusDevice, DeviceType
from .shift import ShiftingSystemID

_logger = logging.getLogger(__name__)


class ValveState(Enum):
    Locked = 0
    Unlocked = 1
    Unknown = 2


class DelayIndicator(Enum):
    Configurable = 0
    NotConfigurable = 1
    Unknown = 2


@dataclass
class DropperSeatpostData(DeviceData):
    """ANT+ dropper seatpost data (shift)"""

    configured_unlock_delay: float = field(default=0x7F, metadata={"unit": "s"})
    delay_indicator: DelayIndicator = DelayIndicator.Unknown
    valve_state: ValveState = ValveState.Unknown
    lock_setting: ValveState = ValveState.Unknown
    slave_serial: int = 0xFFFF
    command_sequence: int = 0


class DropperSeatpost(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "dropper_seatpost",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.DropperSeatpost.value,
            device_id=device_id,
            period=8192,
            name=name,
            trans_type=trans_type,
        )

        self._event_count = [0, 0]

        self.data = {**self.data, "dropper_seatpost": DropperSeatpostData()}

    def _on_battery(self, data: BatteryData):
        if data.battery_id != 0xFF:
            battery_id = ShiftingSystemID(data.battery_id)
            _logger.info(f"Dropper seatpost {battery_id.name} battery update {data}")
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
            self._event_count[1] = int.from_bytes(data[4:6], byteorder="little")

            delay = data[6] & 0x7F
            self.data["dropper_seatpost"].configured_unlock_delay = (
                0x7F if delay == 0x7F else delay * 1e-2
            )  # in 100 ms
            self.data["dropper_seatpost"].delay_indicator = DelayIndicator(
                (data[6] & 0x80 >> 7)
            )
            self.data["dropper_seatpost"].valve_state = ValveState(
                (data[7] & 0x80) >> 7
            )

            delta_update_count = (
                self._event_count[1] + 256 - self._event_count[0]
            ) % 256

            # if it's a new event (count change)
            if delta_update_count:
                _logger.info(
                    f"Seat post state change {self}: {self.data['dropper_seatpost']}"
                )
                self.on_device_data(
                    page, "dropper_seatpost_status", self.data["dropper_seatpost"]
                )
        # settings page
        elif page == 0x20:
            self.data["dropper_seatpost"].slave_serial = int.from_bytes(
                data[1:3], byteorder="little"
            )
            self.data["dropper_seatpost"].command_sequence = data[
                3
            ]  # increment with each command
            self.data["dropper_seatpost"].lock_setting = ValveState(
                data[4] & 0x01
            )  # other bits reserved

    def set_data(
        self,
        data: DropperSeatpostData,
        store_unlock_delay=False,
    ):
        page = [0x00] * 8
        page[0] = 0x20
        data.command_sequence += 1
        page[3] = data.command_sequence
        page[4] = data.lock_setting.value & 0x01
        page[7] = (
            int(data.configured_unlock_delay * 100) & 0x7F
            if int(data.configured_unlock_delay) != 0x7F
            else 0x7F
        )
        page[7] |= (1 << 7) if store_unlock_delay else 0x00

        self.channel.send_acknowledged_data(page)

    def set_valve(self, state: ValveState):
        self.data["dropper_seatpost"].lock_setting = state
        self.set_data(self.data["dropper_seatpost"])
