import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ..easy.node import Node
from .common import AntPlusDevice, DeviceData, DeviceType

_logger = logging.getLogger(__name__)


class LightType(Enum):
    Headlight = 0
    Taillight = 2
    SignalLightConfigurable = 3
    SignalLightLeft = 4
    SignalLightRight = 5
    Other = 7
    Reserved = 1

    @classmethod
    def _missing_(cls, _):
        return LightType.Reserved


class BatteryWarning(Enum):
    Reserved = 0
    New = 1
    Good = 2
    Ok = 3
    Low = 4
    Critical = 5
    Charging = 6
    Invalid = 7

    @classmethod
    def _missing_(cls, _):
        return BatteryWarning.Invalid


class LightBeam(Enum):
    Low = 0
    High = 1


class LightMode(Enum):
    Off = 0
    Steady81To100 = 1
    Steady61To80 = 2
    Steady41To60 = 3
    Steady21To40 = 4
    Steady0To20 = 5
    SlowFlash = 6
    FastFlash = 7
    RandomFlash = 8
    Auto = 9
    TurnSignalLeftSelfCancel = 10
    TurnSignalLeftOngoing = 11
    TurnSignalRightSelfCancel = 12
    TurnSignalRightOngoing = 13
    Hazard = 14
    Reserved = 15  # 15-47
    Custom = 48  # 48-63

    @classmethod
    def _missing_(cls, value):
        if 15 <= value <= 47:
            return LightMode.Reserved
        if 48 <= value <= 63:
            return LightMode.Custom
        return LightMode.Reserved


class LightStateSetting(Enum):
    """Light state for the connect command (page 33)"""

    DoNotChange = 0
    Off = 1
    Flashing = 2
    Steady = 3


# Light intensity sentinel values (data page 1, byte 7)
LIGHT_INTENSITY_BRAKE_OVERRIDE = 0xFD
LIGHT_INTENSITY_AUTO = 0xFE
LIGHT_INTENSITY_INVALID = 0xFF
BEAM_FOCUS_INVALID = 0xFF
SUB_LIGHT_INTENSITY_AUTO = 0x7E
SUB_LIGHT_INTENSITY_INVALID = 0x7F


@dataclass
class SubLightData:
    """State of a single sub-light from data page 3"""

    sub_light_index: int = 0
    light_type: LightType = LightType.Other
    beam: LightBeam = LightBeam.Low
    mode: LightMode = LightMode.Off
    mode_raw: int = 0
    intensity: int = SUB_LIGHT_INTENSITY_INVALID
    battery_warning: bool = False


@dataclass
class BicycleLightsData(DeviceData):
    """ANT+ bicycle light state from data page 1"""

    light_index: int = 0
    bike_radar_support: bool = False
    light_type: LightType = LightType.Headlight
    battery_status: BatteryWarning = BatteryWarning.Invalid
    number_of_sub_lights: int = 0
    last_command_sequence: int = 0xFF
    beam_focus: int = field(default=BEAM_FOCUS_INVALID, metadata={"unit": "%"})
    beam: LightBeam = LightBeam.Low
    mode: LightMode = LightMode.Off
    mode_raw: int = 0
    intensity: int = field(default=LIGHT_INTENSITY_INVALID, metadata={"unit": "%"})


@dataclass
class BicycleLightsCapabilities(DeviceData):
    """ANT+ bicycle light capabilities from data page 2"""

    light_index: int = 0
    auto_intensity_supported: bool = False
    high_low_beam_supported: bool = False
    number_of_supported_modes: int = 0
    battery_capacity_mah: int = 0
    supported_secondary_lights: int = 0
    beam_focus_control_capable: bool = False
    beam_intensity_control_capable: bool = False
    synchronous_brake_light_supported: bool = False
    supported_standard_modes: int = 0  # raw 15-bit field (LSB byte 5, MSB bits 0:6 byte 6)
    supported_light_types: int = 0  # raw bit field, byte 7


class BicycleLights(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "bicycle_lights",
        trans_type: int = 0,
    ):
        super().__init__(
            node,
            device_type=DeviceType.BicycleLights.value,
            device_id=device_id,
            period=4084,  # ~8.02 Hz per ANT+ spec
            name=name,
            trans_type=trans_type,
        )

        self.data = {
            **self.data,
            "lights": BicycleLightsData(),
            "lights_capabilities": BicycleLightsCapabilities(),
            "sub_lights": {},  # type: Dict[int, SubLightData]
        }

    def _decode_sub_light(
        self, index: int, type_byte: int, state_byte: int, intensity_byte: int
    ) -> SubLightData:
        return SubLightData(
            sub_light_index=index,
            light_type=LightType((type_byte >> 3) & 0x07),
            beam=LightBeam((state_byte >> 1) & 0x01),
            mode=LightMode((state_byte >> 2) & 0x3F),
            mode_raw=(state_byte >> 2) & 0x3F,
            intensity=intensity_byte & 0x7F,
            battery_warning=bool(intensity_byte & 0x80),
        )

    def on_data(self, data):
        page = data[0]

        _logger.debug(f"{self} on_data: {data}")

        # Light States 1
        if page == 0x01:
            d = self.data["lights"]
            d.light_index = data[1] & 0x3F
            d.bike_radar_support = bool((data[2] >> 1) & 0x01)
            d.light_type = LightType((data[2] >> 2) & 0x07)
            d.battery_status = BatteryWarning((data[2] >> 5) & 0x07)
            d.number_of_sub_lights = data[3] & 0x07
            d.last_command_sequence = data[4]
            d.beam_focus = data[5]
            d.beam = LightBeam((data[6] >> 1) & 0x01)
            mode_raw = (data[6] >> 2) & 0x3F
            d.mode_raw = mode_raw
            d.mode = LightMode(mode_raw)
            d.intensity = data[7]

            self.on_device_data(page, "light_states", d)

        # Light Capabilities
        elif page == 0x02:
            c = self.data["lights_capabilities"]
            c.light_index = data[1] & 0x3F
            c.auto_intensity_supported = bool(data[2] & 0x01)
            c.high_low_beam_supported = bool((data[2] >> 1) & 0x01)
            c.number_of_supported_modes = (data[2] >> 2) & 0x3F
            c.battery_capacity_mah = (
                data[3] * 200 if data[3] != 0xFF else 0
            )
            c.supported_secondary_lights = data[4] & 0x0F
            # Bit 6: beam focus control (0 capable, 1 incapable — inverted)
            c.beam_focus_control_capable = ((data[4] >> 6) & 0x01) == 0
            c.beam_intensity_control_capable = bool((data[4] >> 7) & 0x01)
            c.supported_standard_modes = data[5] | ((data[6] & 0x7F) << 8)
            c.synchronous_brake_light_supported = bool((data[6] >> 7) & 0x01)
            c.supported_light_types = data[7]

            self.on_device_data(page, "light_capabilities", c)

        # Sub-light State (two sub-lights packed per page)
        elif page == 0x03:
            sub_a_index = data[2] & 0x07
            sub_a = self._decode_sub_light(sub_a_index, data[2], data[3], data[4])
            self.data["sub_lights"][sub_a_index] = sub_a
            self.on_device_data(page, "sub_light_state", sub_a)

            # Bytes 5:7 set to 0 if no second sub-light; otherwise sub_a + 1
            if data[5] != 0x00 or data[6] != 0x00 or data[7] != 0x00:
                sub_b_index = sub_a_index + 1
                sub_b = self._decode_sub_light(sub_b_index, data[5], data[6], data[7])
                self.data["sub_lights"][sub_b_index] = sub_b
                self.on_device_data(page, "sub_light_state", sub_b)

    def set_light(
        self,
        light_index: int = 0,
        sub_light_index: int = 0,
        address_all_sub_lights: bool = False,
        light_type: LightType = LightType.Headlight,
        mode: Optional[LightMode] = None,
        beam: LightBeam = LightBeam.Low,
        intensity: Optional[int] = None,
        controller_id: int = 0,
    ):
        """Send a Light Settings command (page 34) to control the light.

        :param light_index: 0 = all lights, 1-63 = specific light
        :param sub_light_index: 0 = principal light only, 1-4 = specific sub-light
        :param address_all_sub_lights: when True, ignore sub_light_index and address all
        :param mode: LightMode to set; if None, leaves mode unchanged
        :param beam: high/low beam selection (only used if mode is set)
        :param intensity: 0-100 percent intensity to set; if None, no intensity adjustment
        """
        page = [0x00] * 8
        page[0] = 0x22  # data page 34
        page[1] = light_index & 0x3F

        # Light type field is only honored when light_index=0, sub_light_index=0,
        # and address_all_sub_lights=1 (per spec 7.18.4); otherwise leave invalid.
        light_type_field = light_type.value & 0x0F if light_type is not None else 0x0F
        page[2] = (
            (sub_light_index & 0x07)
            | ((1 if address_all_sub_lights else 0) << 3)
            | ((light_type_field & 0x0F) << 4)
        )

        self._command_sequence = (getattr(self, "_command_sequence", 0) + 1) & 0xFF
        page[3] = self._command_sequence
        page[4] = controller_id & 0xFF

        # Beam Adjustment Specifier in byte 5: bit 4 = 0 means "adjust beam focus"
        # (i.e. byte 7 contains a focus value), bit 4 = 1 means "do not adjust focus".
        # bit 5 = 1 means "adjust intensity". Default to "no adjustments".
        adjust_byte = 0b00010000  # bit 4 set = do not adjust focus
        beam_adjustment = 0xFF
        if intensity is not None:
            adjust_byte |= 0b00100000  # bit 5 set = adjust intensity
            beam_adjustment = max(0, min(100, intensity)) & 0xFF
        page[5] = adjust_byte

        # Set Light State byte: combine beam (bit 1) and mode (bits 2:7).
        if mode is not None:
            page[6] = ((beam.value & 0x01) << 1) | ((mode.value & 0x3F) << 2)
        else:
            page[6] = 0x00
        page[7] = beam_adjustment

        self.send_acknowledged_data(page)

    def disconnect(self, light_index: int = 0, controller_id: int = 0):
        """Send a Disconnect command (page 32). light_index=0 disconnects all lights."""
        page = [0x00] * 8
        page[0] = 0x20
        page[1] = light_index & 0x3F
        page[2] = controller_id & 0xFF
        self.send_acknowledged_data(page)

    def request_dp(
        self,
        page: int = 0x01,
        no_times: int = 1,
        light_index: int = 0,
        descriptor_1: int = 63,
        descriptor_2: int = 0xFF,
    ):
        """
        Request a data page from this bike light using common page 70 (0x46).

        Per spec section 7.22.3 / Table 7-45, byte 1 carries the Light Index in
        this profile (not the slave serial LSB used in the base class).

        descriptor_1 defaults to 63 because the only profile-defined page that
        consumes it is page 5 (Mode Description), where it identifies which
        mode to describe. Per spec section 5.3 supported custom modes are
        numbered "from 63 down with no gaps", so 63 is always supported when
        the light has any custom modes; pages that do not use a sub-page
        descriptor ignore the field.

        :param page: data page number to request
        :param no_times: number of times the light should transmit the page
        :param light_index: 0 = all/unconnected lights, 1-63 = specific light
        :param descriptor_1: sub-page descriptor 1 (e.g. mode number for
            page 5); 0xFF when explicitly unused
        :param descriptor_2: sub-page descriptor 2 (0xFF when not used)
        """
        data = [
            0x46,
            light_index & 0x3F,
            0xFF,
            descriptor_1 & 0xFF,
            descriptor_2 & 0xFF,
            no_times & 0x7F,
            page & 0xFF,
            0x01,
        ]
        _logger.info(
            f"{self} requesting data page {page:#04x} "
            f"(light_index={light_index}, no_times={no_times})"
        )
        self.send_acknowledged_data(data)
