from .device import AntPlusDevice

import logging

_logger = logging.getLogger("ant.antplus.BSC")

# bicycle speed / bicycle cadence combined sensor
class BSBCDevice(AntPlusDevice):
    CHANNEL_PERIOD = 8086
    DEVICE_TYPE = 121
    PI = 3.14159  # convert wheel diameter to total distance

    def get_manufacturer_info(self):
        # overwrite base class, because this doesn't exist for cbsc
        pass

    def get_product_info(self):
        # overwrite base class, because this doesn't exist for cbsc
        pass

    def get_command_status(self):
        # overwrite base class, because this doesn't exist for cbsc
        pass

    def __init__(self, node, device_number, device_type, transmission_type):
        if device_type != BSBCDevice.DEVICE_TYPE:
            # TODO : eigenlijk willen we hier een error genereren en een leeg object teruggeven
            print(
                f"Error, device_type = {device_type} is not a Combined Bicycle Speed/Cadence device!"
            )
            return
        channel_period = BSBCDevice.CHANNEL_PERIOD

        super().__init__(
            node, device_number, device_type, transmission_type, channel_period
        )
        # specific init for the FE-C device
        self.status["cadence_event_time"] = 0.0  # seconds
        self.status["speed_event_time"] = 0.0  # seconds
        self.status["crank_rev_count"] = 0
        self.status["wheel_rev_count"] = 0
        self.status["wheel_diameter"] = 0.7

    def set_wheel_diameter(self, diameter):
        self.status["wheel_diameter"] = diameter

    def on_antplus_bcdata(self, data):
        _logger.info(f"got bsc data : {data}")
        # TODO : cleanup the rollover code
        # cadence_event_time
        last_cadence_event_time = self.status[
            "cadence_event_time"
        ]  # for instant_cadence
        last_cadence_event_time_bytes = int(1024 * last_cadence_event_time)
        last_crank_rev_count = self.status["crank_rev_count"]
        new_cadence_event_time_bytes = int.from_bytes(data[0:2], byteorder="little")
        new_cadence_event_time = new_cadence_event_time_bytes / 1024.0
        self.status["cadence_event_time"] = (
            (last_cadence_event_time_bytes & ~0xFFFF) + new_cadence_event_time_bytes
        ) / 1024.0
        if new_cadence_event_time_bytes < (
            last_cadence_event_time_bytes & 0xFFFF
        ):  # rollover happened
            self.status["cadence_event_time"] += 64.0

        # speed_event_time
        last_speed_event_time = self.status["speed_event_time"]  # for instant_speed
        last_speed_event_time_bytes = int(1024 * last_speed_event_time)
        last_wheel_rev_count = self.status["wheel_rev_count"]
        new_speed_event_time_bytes = int.from_bytes(data[4:6], byteorder="little")
        new_speed_event_time = new_speed_event_time_bytes / 1024.0
        self.status["speed_event_time"] = (
            (last_speed_event_time_bytes & ~0xFFFF) + new_speed_event_time_bytes
        ) / 1024.0
        if new_speed_event_time_bytes < (
            last_speed_event_time_bytes & 0xFFFF
        ):  # rollover happened
            self.status["speed_event_time"] += 64.0

        # crank_rev_count
        new_crank_rev_count_bytes = int.from_bytes(data[2:4], byteorder="little")
        if new_crank_rev_count_bytes < (
            last_crank_rev_count & 0xFFFF
        ):  # rollover happened
            self.status["crank_rev_count"] += 0xFFFF
        self.status["crank_rev_count"] = (
            self.status["crank_rev_count"] & ~0xFFFF
        ) + new_crank_rev_count_bytes

        # wheel_rev_count
        new_wheel_rev_count_bytes = int.from_bytes(data[6:8], byteorder="little")
        if new_wheel_rev_count_bytes < (
            last_wheel_rev_count & 0xFFFF
        ):  # rollover happened
            self.status["wheel_rev_count"] += 0xFFFF
        self.status["wheel_rev_count"] = (
            self.status["wheel_rev_count"] & ~0xFFFF
        ) + new_wheel_rev_count_bytes

        # calculated values
        self.status["total_distance"] = (
            self.status["wheel_rev_count"]
            * self.status["wheel_diameter"]
            * BSBCDevice.PI
        )
        if new_cadence_event_time != last_cadence_event_time:
            self.status["instant_cadence"] = int(
                60
                * (self.status["crank_rev_count"] - last_crank_rev_count)
                / (new_cadence_event_time - last_cadence_event_time)
            )  # RPM
        else:
            self.status["instant_cadence"] = 0

        # 3.6 converts m/s to km/h
        if new_speed_event_time != last_speed_event_time:
            self.status["instant_speed"] = (
                BSBCDevice.PI
                * self.status["wheel_diameter"]
                * 3.6
                * (self.status["wheel_rev_count"] - last_wheel_rev_count)
                / (new_speed_event_time - last_speed_event_time)
            )  # km/h
        else:
            self.status["instant_speed"] = 0.0
        # notify callback or polling self.status?

        # don't pass data to base class, because they don't follow the ant+ page format
        # super().on_antplus_bcdata(data)
