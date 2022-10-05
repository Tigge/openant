from . import common
from . import power_meter
from . import fitness_equipment
from . import tire_pressure_monitor
from . import shift
from . import heart_rate

device_profiles = {
    common.DeviceType.PowerMeter: power_meter.PowerMeter,
    common.DeviceType.FitnessEquipment: fitness_equipment.FitnessEquipment,
    common.DeviceType.TirePressureMonitor: tire_pressure_monitor.TirePressureMonitor,
    common.DeviceType.Shifting: shift.Shifting,
    common.DeviceType.HeartRate: heart_rate.HeartRate,
}

__all__ = [
    "common",
    "power_meter",
    "fitness_equipment",
    "tire_pressure_monitor",
    "shift",
]
