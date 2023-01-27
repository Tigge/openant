import logging
from typing import List, Optional

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import DeviceData, AntPlusDevice, DeviceType, BatteryStatus

_logger = logging.getLogger(__name__)


@dataclass
class BikeSpeedData(DeviceData):
    """ANT+ bike speed data."""

    cumulative_operating_time: int = field(default=0, metadata={"unit": "seconds"})
    bike_speed_event_time: List[float] = field(
        default_factory=lambda: [0.0, 0.0], metadata={"unit": "seconds"}
    )
    cumulative_speed_revolution: List[int] = field(
        default_factory=lambda: [0, 0], metadata={"unit": "events"}
    )
    manufacturer_id_lsb: int = 0xFF
    serial_number: int = 0xFFFF

    def calculate_speed(self, wheel_circumference_m: float) -> Optional[float]:
        """
        Returns speed in km/h based on wheel circumference in meters, event time change and revolution change

        :param wheel_circumference_m float: wheel circumference in meters

        >>> bs = BikeSpeedData()
        >>> bs.bike_speed_event_time = [0.0, 1.0]
        >>> bs.cumulative_speed_revolution = [0, 5]
        >>> bs.calculate_speed(2.3)
        41.4
        """
        delta_rev_count = (
            self.cumulative_speed_revolution[1] - self.cumulative_speed_revolution[0]
        )
        delta_event_time = self.bike_speed_event_time[1] - self.bike_speed_event_time[0]
        if delta_event_time > 0:
            return (wheel_circumference_m * delta_rev_count) / delta_event_time * 3.6
        else:
            return None

    def calculate_distance(self, wheel_circumference_m: float) -> float:
        """
        Returns distance based on wheel circumference in meters and the total revolution events

        :param wheel_circumference_m float: wheel circumference in meters

        >>> bs = BikeSpeedData()
        >>> bs.cumulative_speed_revolution = [0, 5]
        >>> bs.calculate_distance(2.3)
        11.5
        """
        return wheel_circumference_m * self.cumulative_speed_revolution[1]


@dataclass
class BikeCadenceData(DeviceData):
    """ANT+ bike cadence data."""

    cumulative_operating_time: int = field(default=0, metadata={"unit": "seconds"})
    bike_cadence_event_time: List[float] = field(
        default_factory=lambda: [0.0, 0.0], metadata={"unit": "seconds"}
    )
    cumulative_cadence_revolution: List[int] = field(
        default_factory=lambda: [0, 0], metadata={"unit": "events"}
    )
    manufacturer_id_lsb: int = 0xFF
    serial_number: int = 0xFFFF

    @property
    def cadence(self):
        """Returns calculate_cadence as a property"""
        return self.calculate_cadence()

    def calculate_cadence(self) -> Optional[float]:
        """Calculates cadence using delta values of RPM and time

        >>> bc = BikeCadenceData()
        >>> bc.bike_cadence_event_time = [0.0, 1.5]
        >>> bc.cumulative_cadence_revolution = [0, 2]
        >>> bc.calculate_cadence()
        80.0
        """
        delta_rev_count = (
            self.cumulative_cadence_revolution[1]
            - self.cumulative_cadence_revolution[0]
        )
        delta_event_time = (
            self.bike_cadence_event_time[1] - self.bike_cadence_event_time[0]
        )
        if delta_event_time > 0:
            return (60 * delta_rev_count) / delta_event_time
        else:
            return None


class BikeSpeed(AntPlusDevice):
    """Device profile for speed sensor"""

    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "bike_speed",
        trans_type: int = 0,
    ):
        # power meter is 11 so make ANT+ device with that device type
        super().__init__(
            node,
            device_type=DeviceType.BikeSpeed.value,
            device_id=device_id,
            period=8118,
            name=name,
            trans_type=trans_type,
        )

        self.data = {**self.data, "bike_speed": BikeSpeedData()}

    @staticmethod
    def update_speed_data(bike_speed_data: BikeSpeedData, data: List[int]):
        if len(data) != 4:
            raise ValueError("data length must be == 4")

        bike_speed_event_time = (
            int.from_bytes(data[0:2], byteorder="little") / 1024
        )  # 1/1024 seconds
        bike_speed_data.bike_speed_event_time[
            0
        ] = bike_speed_data.bike_speed_event_time[1]
        bike_speed_data.bike_speed_event_time[1] = bike_speed_event_time
        cumulative_speed_revolution = int.from_bytes(data[2:4], byteorder="little")
        bike_speed_data.cumulative_speed_revolution[
            0
        ] = bike_speed_data.cumulative_speed_revolution[1]
        bike_speed_data.cumulative_speed_revolution[1] = cumulative_speed_revolution

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # MSB is page change toggle, 0-7 can be rotated with page specific data but all include these bytes
        if (page & 0x0F) <= 7:
            dp = page & 0x0F

            # default/unknown
            if dp == 0x00:
                self.update_speed_data(self.data["bike_speed"], data[4:8])
            # comulative operating time
            elif dp == 0x01:
                self.data["bike_speed"].cumulative_operating_time = (
                    int.from_bytes(data[1:4], byteorder="little") * 2
                )  # 2 second units
                self.update_speed_data(self.data["bike_speed"], data[4:8])
            # manufacturer ID
            elif dp == 0x02:
                self.data["bike_speed"].manufacturer_id_lsb = data[1]
                self.data["bike_speed"].serial_number = int.from_bytes(
                    data[2:4], byteorder="little"
                )
                self.update_speed_data(self.data["bike_speed"], data[4:8])
            # background page product info
            elif dp == 0x03:
                self.update_speed_data(self.data["bike_speed"], data[4:8])
            elif dp == 0x04:
                self.data["common"].last_battery_data.voltage_fractional = data[2] / 256
                self.data["common"].last_battery_data.voltage_coarse = data[3] & 0x0F
                self.data["common"].last_battery_data.status = BatteryStatus(
                    (data[3] & 0x70) >> 4
                )
                self.update_speed_data(self.data["bike_speed"], data[4:8])
                # trigger the on battery callback
                self._on_battery(self.data["common"].last_battery_data)
            # motion and speed
            elif dp == 0x05:
                self.update_speed_data(self.data["bike_speed"], data[4:8])

            self.on_device_data(page, "bike_speed", self.data["bike_speed"])


class BikeCadence(AntPlusDevice):
    """Device profile for cadence sensor"""

    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "bike_cadence",
        trans_type: int = 0,
    ):
        # power meter is 11 so make ANT+ device with that device type
        super().__init__(
            node,
            device_type=DeviceType.BikeCadence.value,
            device_id=device_id,
            period=8102,
            name=name,
            trans_type=trans_type,
        )

        self.data = {**self.data, "bike_cadence": BikeCadenceData()}

    @staticmethod
    def update_cadence_data(bike_cadence_data: BikeCadenceData, data: List[int]):
        if len(data) != 4:
            raise ValueError("data length must be == 4")

        bike_cadence_event_time = (
            int.from_bytes(data[0:2], byteorder="little") / 1024
        )  # 1/1024 seconds
        bike_cadence_data.bike_cadence_event_time[
            0
        ] = bike_cadence_data.bike_cadence_event_time[1]
        bike_cadence_data.bike_cadence_event_time[1] = bike_cadence_event_time
        cumulative_cadence_revolution = int.from_bytes(data[2:4], byteorder="little")
        bike_cadence_data.cumulative_cadence_revolution[
            0
        ] = bike_cadence_data.cumulative_cadence_revolution[1]
        bike_cadence_data.cumulative_cadence_revolution[
            1
        ] = cumulative_cadence_revolution

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # MSB is page change toggle, 0-7 can be rotated with page specific data but all include these bytes
        if (page & 0x0F) <= 7:
            dp = page & 0x0F

            # default/unknown
            if dp == 0x00:
                self.update_cadence_data(self.data["bike_cadence"], data[4:8])
            # comulative operating time
            elif dp == 0x01:
                self.data["bike_cadence"].cumulative_operating_time = (
                    int.from_bytes(data[1:4], byteorder="little") * 2
                )  # 2 second units
                self.update_cadence_data(self.data["bike_cadence"], data[4:8])
            # manufacturer ID
            elif dp == 0x02:
                self.data["bike_cadence"].manufacturer_id_lsb = data[1]
                self.data["bike_cadence"].serial_number = int.from_bytes(
                    data[2:4], byteorder="little"
                )
                self.update_cadence_data(self.data["bike_cadence"], data[4:8])
            # background page product info
            elif dp == 0x03:
                self.update_cadence_data(self.data["bike_cadence"], data[4:8])
            elif dp == 0x04:
                self.data["common"].last_battery_data.voltage_fractional = data[2] / 256
                self.data["common"].last_battery_data.voltage_coarse = data[3] & 0x0F
                self.data["common"].last_battery_data.status = BatteryStatus(
                    (data[3] & 0x70) >> 4
                )
                self.update_cadence_data(self.data["bike_cadence"], data[4:8])
                # trigger the on battery callback
                self._on_battery(self.data["common"].last_battery_data)
            # motion and cadence
            elif dp == 0x05:
                self.update_cadence_data(self.data["bike_cadence"], data[4:8])

            self.on_device_data(page, "bike_cadence", self.data["bike_cadence"])


class BikeSpeedCadence(AntPlusDevice):
    """Device profile for speed and cadence sensor, only broadcasts one device data page"""

    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "bike_speed_cadence",
        trans_type: int = 0,
    ):
        # power meter is 11 so make ANT+ device with that device type
        super().__init__(
            node,
            device_type=DeviceType.BikeSpeedCadence.value,
            device_id=device_id,
            period=8086,
            name=name,
            trans_type=trans_type,
        )

        self.data = {
            **self.data,
            "bike_speed": BikeSpeedData(),
            "bike_cadence": BikeCadenceData(),
        }

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # only one page
        if (page & 0x0F) <= 5:
            BikeCadence.update_cadence_data(self.data["bike_cadence"], data[0:4])
            BikeSpeed.update_speed_data(self.data["bike_speed"], data[4:8])

            self.on_device_data(page, "bike_cadence", self.data["bike_cadence"])
            self.on_device_data(page, "bike_speed", self.data["bike_speed"])
