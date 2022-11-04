"""
ANT+ devices and defines
"""
from . import common
from . import power_meter
from . import fitness_equipment
from . import tire_pressure_monitor
from . import shift
from . import heart_rate
from . import dropper_seatpost
from . import lev
from . import bike_speed_cadence

# standard ANT+ network key
ANTPLUS_NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]

# List of available device profiles used for `auto_create_device`
device_profiles = {
    common.DeviceType.PowerMeter: power_meter.PowerMeter,
    common.DeviceType.FitnessEquipment: fitness_equipment.FitnessEquipment,
    common.DeviceType.TirePressureMonitor: tire_pressure_monitor.TirePressureMonitor,
    common.DeviceType.Shifting: shift.Shifting,
    common.DeviceType.HeartRate: heart_rate.HeartRate,
    common.DeviceType.DropperSeatpost: dropper_seatpost.DropperSeatpost,
    common.DeviceType.Lev: lev.Lev,
    common.DeviceType.BikeSpeed: bike_speed_cadence.BikeSpeed,
    common.DeviceType.BikeCadence: bike_speed_cadence.BikeCadence,
    common.DeviceType.BikeSpeedCadence: bike_speed_cadence.BikeSpeedCadence,
}

__all__ = [
    "common",
    "power_meter",
    "fitness_equipment",
    "tire_pressure_monitor",
    "shift",
    "dropper_seatpost",
    "lev",
    "bike_speed_cadence",
]
