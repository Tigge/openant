from . import common
from . import power_meter
from . import fitness_equipment
from . import tire_pressure_monitor
from . import shift

device_profiles = {
        "PowerMeter": power_meter.PowerMeter, 
        "FitnessEquipment": fitness_equipment.FitnessEquipment,
        "TirePressureMonitor": tire_pressure_monitor.TirePressureMonitor,
        "Shifting": shift.Shifting,
}

__all__ = ["common", "power_meter", "fitness_equipment", "tire_pressure_monitor", "shift"]
