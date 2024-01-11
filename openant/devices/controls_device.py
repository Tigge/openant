import logging
from enum import Enum
from typing import Set, Optional, List

from dataclasses import dataclass, field

from ..easy.node import Node
from .common import DeviceData, AntPlusDevice, DeviceType

_logger = logging.getLogger(__name__)


class ControlCapabilities(Enum):
    AutoControl = 0
    KeypadControl = 3
    GenericControl = 4
    VideoControl = 5
    BurstCommand = 6
    Reserved = 7

    @staticmethod
    def from_byte(byte: int):
        ret = set()
        for i in range(ControlCapabilities.Reserved.value):
            if byte >> i & 0x01:
                ret.add(ControlCapabilities(i))
        return ret

    @staticmethod
    def to_byte(caps: set):
        ret = 0x00
        for c in caps:
            ret |= 1 << c.value
        return ret

    @classmethod
    def _missing_(cls, _):
        return ControlCapabilities.Reserved


class ControlCommand(Enum):
    MenuUp = 0
    MenuDown = 1
    MenuSelect = 2
    MenuBack = 3
    Home = 4
    Start = 32
    Stop = 33
    Reset = 34
    Length = 35
    Lap = 36
    Reserved = 0x7FFF  # 5 - 31, 37 - 32767
    Custom = 0xFFFE  # 32768 - 65534
    NoCommand = 0xFFFF

    @staticmethod
    def from_int(i: int):
        try:
            return ControlCommand(i)
        except:
            if (i >= 5 and i <= 31) or (i >= 37 and i <= 32767):
                return ControlCommand.Reserved
            elif i >= 32768 and i <= 65534:
                return ControlCommand.Custom
            else:
                return ControlCommand.NoCommand


class CommandStatus(Enum):
    Pass = 0
    Fail = 3
    NotSupported = 4
    Rejected = 5
    Pending = 6
    Reserved = 254  # 5 - 254
    Uninitialized = 255

    @classmethod
    def _missing_(cls, _):
        return CommandStatus.Uninitialized


@dataclass
class ControlsDeviceData(DeviceData):
    """ANT+ control device data"""

    slave_serial: int = 0xFFFF
    slave_manufacturer_id: int = 0xFFFF
    capabilities: Set[ControlCapabilities] = field(default_factory=lambda: set())
    current_notifications: int = 0x00
    command_sequence: int = 0  # inc each request
    command_status: CommandStatus = CommandStatus.Uninitialized
    last_received_command_page: int = 0xFF
    last_control_command: ControlCommand = ControlCommand.NoCommand
    response_data: List[int] = field(default_factory=lambda: [0xFF, 0xFF, 0xFF, 0xFF])


class ControlsDevice(AntPlusDevice):
    def __init__(
        self,
        node: Node,
        device_id: int = 0,
        name: str = "controls_device",
        trans_type: int = 0,
        master: bool = False,
    ):
        super().__init__(
            node,
            device_type=DeviceType.ControlsDevice.value,
            device_id=device_id,
            period=8192,
            name=name,
            trans_type=trans_type,
            master=master,
        )

        self.data = {**self.data, "control": ControlsDeviceData()}

    def on_data(self, data):
        # there shouldn't be any extra broadcast pages beyond the common ones handled by parent
        _logger.debug(f"{self} on_data: {data}")

    def on_tx_data(self) -> Optional[List[int]]:
        # Control Device Availability, parent _on_tx_data handles common pages
        return [
            0x02,
            self.data["control"].current_notifications,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,  # reserved
            ControlCapabilities.to_byte(self.data["control"].capabilities),
        ]

    def on_ack_data(self, data) -> Optional[List[int]]:
        """Commands are sent as ACK"""
        page = data[0]

        # generic command page
        if page == 0x49:
            self.data["control"].command_sequence = data[5]
            command = data[6] + (data[7] << 8)
            command_enum = ControlCommand.from_int(command)
            _logger.debug(f"Received {command_enum}")
            # callback for command
            self.on_control_command(command_enum, command)
            # local callback to setup command status page
            self._on_command(page)
            self._on_control_command(command_enum, command)
        # audio/video
        elif page == 0x10:
            # TODO process and callback
            _logger.debug(f"Recieved audio/video request without action")
            pass
        # character
        elif page == 0x11:
            # TODO process and callback
            _logger.debug(f"Recieved character request without action")
            pass
        # command status
        elif page == 0x47:
            payload = [
                0x47,
                self.data["control"].last_received_command_page,
                self.data["control"].command_sequence,
                self.data["control"].command_status,
                self.data["control"].response_data,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
            payload[4:8] = self.data["control"].response_data

            return payload

    def _on_command(self, page: int):
        # ensure command status has been set
        if (
            self.data["control"].command_status.value
            == CommandStatus.Uninitialized.value
        ):
            self.data["control"].command_status = CommandStatus.Pass
        # save last data
        self.data["control"].last_received_command_page = page

    def _on_control_command(self, command: ControlCommand, raw: int):
        self.data["control"].last_control_command = command
        # table 11-4
        self.data["control"].response_data = [raw & 0xFF, (raw >> 8) & 0xFF, 0xFF, 0xFF]

    @staticmethod
    def on_control_command(command: ControlCommand, raw: int):
        """Override for on control command"""
        assert command, raw
        pass

    def send_control_command_raw(self, command_int: int):
        page = [0x00] * 8
        page[0] = 0x49  # command page

        data = self.data["control"]
        data.command_sequence += 1

        page[1] = data.slave_serial & 0xFF
        page[2] = (data.slave_serial >> 8) & 0xFF
        page[3] = data.slave_manufacturer_id & 0xFF
        page[4] = (data.slave_manufacturer_id >> 8) & 0xFF
        page[5] = data.command_sequence
        page[6] = command_int & 0xFF
        page[7] = (command_int >> 8) & 0xFF

        self.channel.send_acknowledged_data(page)

    def send_control_command(self, command: ControlCommand):
        """Send a generic control command"""
        self.send_control_command_raw(command.value)

    # TODO command busrt


class GenericRemoteControl(ControlsDevice):
    def __init__(self, node: Node, device_id=0):
        super().__init__(
            node,
            device_id=device_id,
            master=False,
            name="generic_remote",
        )

        self.data["control"].capabilities.add(ControlCapabilities.GenericControl)


class GenericControllableDevice(ControlsDevice):
    def __init__(self, node: Node, device_id=0):
        super().__init__(
            node,
            device_id=device_id,
            master=True,
            name="generic_controllable_device",
        )

        self.data["control"].capabilities.add(ControlCapabilities.GenericControl)
