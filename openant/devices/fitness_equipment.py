import time
import array
import threading
import queue
import logging
import math

from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..easy.node import Node

from .common import DeviceData, AntPlusDevice, DeviceType
from .power_meter import PowerData

_logger = logging.getLogger(__name__)


class ResistenceMode(Enum):
    Basic = 0x30
    TargetPower = 0x31
    Wind = 0x32
    Track = 0x33
    Unknown = 0xFF

    @classmethod
    def _missing_(cls, _):
        return ResistenceMode.Unknown


class CommandStatus(Enum):
    Pass = 0
    Fail = 1
    NotSupported = 2
    Rejected = 3
    Pending = 4
    Unknown = "null"
    Unitialised = 0xFF

    # between 5-254
    @classmethod
    def _missing_(cls, _):
        return CommandStatus.Unknown


class FitnessEquipmentState(Enum):
    Unknown = 0
    Asleep = 1
    Ready = 2
    InUse = 3
    Finished = 4

    @classmethod
    def _missing_(cls, _):
        return FitnessEquipmentState.Unknown


class FitnessEquipmentType(Enum):
    Treadmill = 19
    Eliptical = 20
    Rower = 22
    Climber = 23
    NordicSkier = 24
    Trainer = 25
    Reserved = 0

    @classmethod
    def _missing_(cls, _):
        return FitnessEquipmentType.Reserved


@dataclass
class FitnessEquipmentData(DeviceData):
    """
    ANT+ FE data
    """

    resistance_mode: ResistenceMode = ResistenceMode.Unknown
    resistance: float = 255.0
    state: FitnessEquipmentState = FitnessEquipmentState.Unknown
    type: FitnessEquipmentType = FitnessEquipmentType.Reserved
    capabilities: int = 0
    speed: float = 65535.0
    incline: float = 32767.0
    target_resistance: float = 255.0


@dataclass
class Workout:
    """
    Workout to use with FE device
    """

    intervals: List[Tuple]
    cycles: int = 1
    loop: bool = False

    @staticmethod
    def from_arrays(powers: List[int], periods: List[float], **kwargs):
        """
        Create workout from arrays of powers and periods

        :param powers List[int]: power setpoints
        :param periods List[float]: period to hold each power (s)
        :raises ValueError: powers and periods not equal length

        >>> Workout.from_arrays([100, 200, 300, 400], [5, 5.5, 10.2, 11.1])
        Workout(intervals=[(100, 5), (200, 5.5), (300, 10.2), (400, 11.1)], cycles=1, loop=False)
        """
        if len(powers) != len(periods):
            raise ValueError("Power levels and periods must be equal in length")

        return Workout(intervals=[*zip(powers, periods)], **kwargs)

    @staticmethod
    def from_ramp(
        start: int,
        stop: int,
        step: int,
        period: float,
        peak: Optional[int] = None,
        **kwargs,
    ):
        """
        Build Workout from `start`, `stop` and power `step` with `period` between

        :param start int: start power (W)
        :param stop int: stop power (W)
        :param step int: step power (W)
        :param period float: period at each level (s)
        :param peak int: peak power if triangle wave (W)
        :raises ValueError: start > stop, stop < start, step == 0, period == 0, peak != 0 && peak < stop | peak < start

        >>> Workout.from_ramp(100, 500, 50, 10.0)
        Workout(intervals=[(100, 10.0), (150, 10.0), (200, 10.0), (250, 10.0), (300, 10.0), (350, 10.0), (400, 10.0), (450, 10.0)], cycles=1, loop=False)
        >>> Workout.from_ramp(100, 100, 50, 10.0, peak=500, cycles=4)
        Workout(intervals=[(100, 10.0), (150, 10.0), (200, 10.0), (250, 10.0), (300, 10.0), (350, 10.0), (400, 10.0), (450, 10.0), (500, 10.0), (450, 10.0), (400, 10.0), (350, 10.0), (300, 10.0), (250, 10.0), (200, 10.0), (150, 10.0)], cycles=4, loop=False)
        """
        if start > stop:
            raise ValueError("Start power must be less than stop power")

        if stop < start:
            raise ValueError("Stop power must be greater than start power")

        if step == 0 or period == 0:
            raise ValueError("Step or period cannot be zero")

        if peak and (peak < stop or peak < start):
            raise ValueError(
                "Peak value if used must be greater than start and stop value"
            )

        if peak:
            intervals = [(power, period) for power in range(start, peak, step)]
            intervals += [(power, period) for power in range(peak, stop, step * -1)]
        else:
            intervals = [(power, period) for power in range(start, stop, step)]

        return Workout(intervals=intervals, **kwargs)


class FitnessEquipment(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "fitness_equipment",
        trans_type: int = 0,
    ):
        # fitness equipment is 17 so make ANT+ device with that device type
        super().__init__(
            node,
            device_type=DeviceType.FitnessEquipment.value,
            device_id=device_id,
            period=8192,
            name=name,
            trans_type=trans_type,
        )

        self.command_status = CommandStatus.Unknown
        self._power_update_event_count = [0, 0]
        self._accumulated_power = [0, 0]

        self._torque_update_event_count = [0, 0]
        self._wheel_ticks = [0, 0]
        self._accumulated_torque = [0, 0]
        self._wheel_period = [0, 0]

        self.resistance_mode = ResistenceMode.Unknown

        self._stopper = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._worker, name="fe_workout", daemon=True
        )
        self._workout_queue = queue.Queue()

        self.data = {**self.data, "power": PowerData(), "fe": FitnessEquipmentData()}

    def start_workouts(self, workouts: List[Workout]):
        for w in workouts:
            self._workout_queue.put(w)

        if not self._worker_thread.is_alive():
            self._worker_thread.start()

    def run_workout(self, workout: Workout):
        intervals = workout.intervals

        for x in range(workout.cycles):
            i = 0

            for power, t in intervals:
                _logger.info(
                    f"{'Looping' if workout.loop else 'Non-looping'} workout cycle {x} of {workout.cycles}, interval {i} of {len(intervals)}: {power} W for {t} seconds"
                )
                self.set_target_power(power)
                i += 1
                time.sleep(t)

    def _worker(self):
        while not self._stopper.is_set():
            # sit waiting for a workout
            workout = self._workout_queue.get()

            if workout.loop:
                while workout.loop:
                    self.run_workout(workout)
            else:
                self.run_workout(workout)

    def on_data(self, data: array.array):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # standard power
        if page == 0x19:
            self._power_update_event_count[0] = self._power_update_event_count[1]
            self._power_update_event_count[1] = data[1]

            self._accumulated_power[0] = self._accumulated_power[1]
            self._accumulated_power[1] = data[3] + (data[4] << 8)

            self.data["power"].cadence = data[2]
            self.data["power"].instantaneous_power = data[5] + ((data[6] & 0x0F) << 8)

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
        elif page == 0x1A:
            self._torque_update_event_count[0] = self._torque_update_event_count[1]
            self._torque_update_event_count[1] = data[1]

            self._wheel_ticks[0] = self._wheel_ticks[1]
            self._wheel_ticks[1] = data[2]

            self._wheel_period[0] = self._wheel_period[1]
            self._wheel_period[1] = data[4] + (data[5] << 8)

            self._accumulated_torque[0] = self._accumulated_torque[1]
            self._accumulated_torque[1] = data[6] + (data[7] << 8)

            # do the maths on new data
            delta_update_count = (
                self._torque_update_event_count[1]
                + 256
                - self._torque_update_event_count[0]
            ) % 256
            delta_torque = (
                self._accumulated_torque[1] + 65536 - self._accumulated_torque[0]
            ) % 65536
            delta_wheel_period = (
                self._wheel_period[1] + 65536 - self._wheel_period[0] % 65536
            )

            self.data["fe"].state = FitnessEquipmentState(data[7] & 0x70 >> 4)

            # if it's a new event (count change)
            if delta_update_count:
                self.data["power"].torque = round(
                    delta_torque / (32 * (delta_update_count)), 2
                )

                if delta_wheel_period:
                    self.data["power"].angular_velocity = round(
                        (2 * math.pi * delta_update_count)
                        / (delta_wheel_period / 2048),
                        2,
                    )
                else:
                    self.data["power"].angular_velocity = 0

                self.data["power"].average_power = int(
                    self.data["power"].torque * self.data["power"].angular_velocity
                )

                _logger.info(
                    f"Standard torque update {self}: {self.data['power'].average_power} W; Angular Velocity {self.data['power'].angular_velocity} rad/s; Average Torque: {self.data['power'].torque} Nm"
                )

                self.on_device_data(page, "standard_torque", self.data["power"])
        # general FE data
        elif page == 0x10:
            self.data["fe"].type = data[1]
            self.data["fe"].capabilities = data[2] & 0x0F
            self.data["fe"].speed = round((data[4] + (data[5] << 8)) / 1000, 3)
            self.data["fe"].state = FitnessEquipmentState(data[7] & 0x70 >> 4)

            _logger.info(
                f"General FE {self}: Type: {self.data['fe'].type}; State: {self.data['fe'].state}"
            )

            self.on_device_data(page, "general_fe", self.data["fe"])
        # general settings
        elif page == 0x11:
            self.data["fe"].type = data[1]
            self.data["fe"].resistance = round(data[6] / 2, 1)
            incline = data[4] + (data[5] << 8)
            if incline != 0x7FFF:
                self.data["fe"].incline = round(incline / 100, 2)  # 0.01 %

            _logger.info(
                f"General settings {self}: Type: {self.data['fe'].type}; Resistence: {self.data['fe'].resistance}"
            )

            self.on_device_data(page, "general_settings", self.data["fe"])
        # datapage reply 71
        elif page == 0x47:
            self.data["fe"].resistance_mode = ResistenceMode(data[1])

            if self.data["fe"].resistance_mode == ResistenceMode.Basic:
                self.data["fe"].resistance = round(data[7] / 2, 1)
            elif self.data["fe"].resistance_mode == ResistenceMode.TargetPower:
                self.data["fe"].resistance = round((data[6] + (data[7] << 8)) / 4, 2)
            # not bothered about the others

            self.command_status = CommandStatus(data[3])

            if self.command_status not in (
                CommandStatus.Pass,
                CommandStatus.Unitialised,
                CommandStatus.Pending,
            ):
                _logger.warning("Last command went wrong: {self.command_status.name}")

            _logger.info(
                f"Command page {self}: {self.command_status}; {self.data['fe'].resistance_mode.name}: {self.data['fe'].resistance}"
            )

    def set_target_power(self, power: int):
        data = [0x31, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0]

        if power > 4000:
            raise ValueError("Target power cannot exceed 4000 W")

        self.data["fe"].target_resistance = power

        # convert to units of 0.25 W
        power *= 4

        data[6] = power & 0xFF
        data[7] = (power >> 8) & 0xFF

        # send request
        self.send_acknowledged_data(data)

        # request dp to confirm change
        self.request_dp(71)

    def set_basic_resistance(self, resistance: float):
        data = [0x30, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0]

        if resistance > 100.0:
            raise ValueError("Target resistance cannot exceed 100%")

        self.data["fe"].target_resistance = resistance

        # convert to units of 0.5%
        resistance *= 2

        data[7] = int(resistance) & 0xFF

        # send request
        self.send_acknowledged_data(data)

        # request dp to confirm change
        self.request_dp(71)

    def close_channel(self):

        if self._worker_thread.is_alive():
            self._stopper.set()

        super().close_channel()
