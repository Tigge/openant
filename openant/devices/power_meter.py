import math
import logging

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import DeviceData, AntPlusDevice, DeviceType

_logger = logging.getLogger(__name__)


@dataclass
class PowerData(DeviceData):
    """ANT+ Power meter data."""

    instantaneous_power: int = field(default=0, metadata={"unit": "Watts"})
    average_power: int = field(default=0, metadata={"unit": "Watts"})
    left_power: int = field(default=-1, metadata={"unit": "Watts"})
    right_power: int = field(default=-1, metadata={"unit": "Watts"})
    torque: float = field(default=0.0, metadata={"unit": "Nm"})
    angular_velocity: float = field(default=0.0, metadata={"unit": "rad/s"})
    cadence: int = field(default=255, metadata={"unit": "rpm"})


class PowerMeter(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "power_meter",
        trans_type: int = 0,
    ):
        # power meter is 11 so make ANT+ device with that device type
        super().__init__(
            node,
            device_type=DeviceType.PowerMeter.value,
            device_id=device_id,
            period=8182,
            name=name,
            trans_type=trans_type,
        )

        self._power_update_event_count = [0, 0]
        self._accumulated_power = [0, 0]

        self._torque_update_event_count = [0, 0]
        self._crank_ticks = [0, 0]
        self._accumulated_torque = [0, 0]
        self._crank_period = [0, 0]

        self.data = {**self.data, "power": PowerData()}

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # standard power
        if page == 0x10:
            self._power_update_event_count[0] = self._power_update_event_count[1]
            self._power_update_event_count[1] = data[1]

            self._accumulated_power[0] = self._accumulated_power[1]
            self._accumulated_power[1] = data[4] + (data[5] << 8)

            self.data["power"].cadence = data[3]
            self.data["power"].instantaneous_power = data[6] + (data[7] << 8)

            # pedal power bit 7 tells us if dual sided and that the percent is the RH
            if data[2] & (1 << 7) and data[2] != 0xFF:
                percent = data[2] ^ (1 << 7)
                self.data["power"].right_power = int(
                    (self.data["power"].instantaneous_power * percent) / 100
                )
                self.data["power"].left_power = (
                    self.data["power"].instantaneous_power
                    - self.data["power"].right_power
                )

            delta_update_count = (
                self._power_update_event_count[1]
                + 256
                - self._power_update_event_count[0]
            ) % 256
            # if it's a new event (count change)
            if delta_update_count:
                self.data["power"].average_power = int(
                    (
                        (
                            self._accumulated_power[1]
                            + 65536
                            - self._accumulated_power[0]
                        )
                        % 65536
                    )
                    / delta_update_count
                )

                _logger.info(
                    f"Standard power update {self}: {self.data['power'].instantaneous_power} W; Average Power: {self.data['power'].average_power} W; Cadence {self.data['power'].cadence} rpm"
                )

                self.on_device_data(page, "standard_power", self.data["power"])

        # standard torque
        elif page == 0x12:
            self._torque_update_event_count[0] = self._torque_update_event_count[1]
            self._torque_update_event_count[1] = data[1]

            self._crank_ticks[0] = self._crank_ticks[1]
            self._crank_ticks[1] = data[2]

            self._crank_period[0] = self._crank_period[1]
            self._crank_period[1] = data[4] + (data[5] << 8)

            self._accumulated_torque[0] = self._accumulated_torque[1]
            self._accumulated_torque[1] = data[6] + (data[7] << 8)

            self.data["power"].cadence = data[3]

            # do the maths on new data
            delta_update_count = (
                self._torque_update_event_count[1]
                + 256
                - self._torque_update_event_count[0]
            ) % 256
            delta_torque = (
                self._accumulated_torque[1] + 65536 - self._accumulated_torque[0]
            ) % 65536
            delta_crank_period = (
                self._crank_period[1] + 65536 - self._crank_period[0] % 65536
            )

            # if it's a new event (count change)
            if delta_update_count:
                self.data["power"].torque = delta_torque / (32 * (delta_update_count))

                if delta_crank_period:
                    self.data["power"].angular_velocity = (
                        2 * math.pi * delta_update_count
                    ) / (delta_crank_period / 2048)
                else:
                    self.data["power"].angular_velocity = 0

                # can use change in torque with period
                # self.average_power = (128 * math.pi * delta_torque) / delta_crank_period
                # or just torque * angular velocity (Nm*rad/s)
                self.data["power"].average_power = int(
                    self.data["power"].torque * self.data["power"].angular_velocity
                )

                _logger.info(
                    f"Standard torque update {self}: {self.data['power'].average_power} W; Angular Velocity {self.data['power'].angular_velocity} rad/s; Average Torque: {self.data['power'].torque} Nm"
                )

                self.on_device_data(page, "standard_torque", self.data["power"])
