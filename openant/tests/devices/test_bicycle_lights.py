import unittest
from unittest.mock import MagicMock

from openant.devices.bicycle_lights import (
    BicycleLights,
    BicycleLightsData,
    BicycleLightsCapabilities,
    LightBeam,
    LightMode,
    LightType,
    BatteryWarning,
)


def _make_lights():
    """Build a BicycleLights without opening an ANT channel."""
    node = MagicMock()
    inst = BicycleLights.__new__(BicycleLights)
    inst.node = node
    inst.name = "bicycle_lights"
    inst.device_id = 0
    inst.data = {
        "lights": BicycleLightsData(),
        "lights_capabilities": BicycleLightsCapabilities(),
        "sub_lights": {},
    }
    inst.channel = MagicMock()
    inst.send_acknowledged_data = MagicMock()
    return inst


class BicycleLightsPage1Decode(unittest.TestCase):
    def test_decodes_taillight_slow_flash_low_battery(self):
        inst = _make_lights()
        # battery=Low (4) << 5 | type=Taillight (2) << 2 | radar (0) << 1 = 0x88
        # mode=SlowFlash (6) << 2 | beam=Low (0) << 1 = 0x18
        BicycleLights.on_data(inst, [0x01, 0x01, 0x88, 0x00, 0xFF, 0xFF, 0x18, 50])
        d = inst.data["lights"]
        self.assertEqual(d.light_index, 1)
        self.assertEqual(d.light_type, LightType.Taillight)
        self.assertEqual(d.battery_status, BatteryWarning.Low)
        self.assertEqual(d.beam, LightBeam.Low)
        self.assertEqual(d.mode, LightMode.SlowFlash)
        self.assertEqual(d.intensity, 50)
        self.assertFalse(d.bike_radar_support)

    def test_custom_mode_falls_into_custom_bucket(self):
        inst = _make_lights()
        # mode=50 (custom range 48-63), beam=High
        b6 = (50 << 2) | (1 << 1)
        BicycleLights.on_data(inst, [0x01, 0, 0, 0, 0xFF, 0xFF, b6, 100])
        self.assertEqual(inst.data["lights"].mode, LightMode.Custom)
        self.assertEqual(inst.data["lights"].mode_raw, 50)
        self.assertEqual(inst.data["lights"].beam, LightBeam.High)


if __name__ == "__main__":
    unittest.main()
