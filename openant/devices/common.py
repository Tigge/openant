"""
Common ANT+ data and parent class for child devices.

When creating a new device using AntPlusDevice as the parent. The `on_data` callback can be used to decode device specific data - see a device in this module as an example.

Creating a device then just requires a openant.easy.node.Node() wtih network configured

.. code-block:: python

    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)
    generic_device = AntPlusDevice(node)
"""
import dataclasses
import datetime
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from ..easy.channel import Channel
from ..easy.exception import AntException
from ..easy.node import Node

_logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """
    ANT+ device profile identifiers
    """

    Unknown = 255
    PowerMeter = 11
    FitnessEquipment = 17
    ControlsDevice = 16
    BloodPressure = 18
    Geocache = 19
    Environment = 25
    TirePressureMonitor = 48
    WeightScale = 119
    HeartRate = 120
    BikeSpeedCadence = 121
    BikeCadence = 122
    BikeSpeed = 123
    StrideSpeed = 124
    Lev = 20
    Radar = 40
    Shifting = 34
    DropperSeatpost = 115

    @classmethod
    def _missing_(cls, _):
        return DeviceType.Unknown


class BatteryStatus(Enum):
    """
    ANT+ battery status
    """

    Unknown = 0
    New = 1
    Good = 2
    Ok = 3
    Low = 4
    Critical = 5
    Charging = 6
    Invalid = 7

    @classmethod
    def _missing_(cls, _):
        return BatteryStatus.Unknown


@dataclass
class DeviceData:
    """
    The base class for device data page dataclasses
    """

    def to_influx_json(self, tags: dict):
        """
        Converts DeviceData into json dict expected by InfluxDB 1 -> `write_points` and compatiable with InfluxDB 2 `write`

        :param tags dict: tags to include in write

        >>> from openant.devices.power_meter import PowerData
        >>> p = PowerData()
        >>> p.to_influx_json({"taggy": "blah"}) #doctest: +ELLIPSIS
        {'measurement': 'PowerData', 'tags': {'taggy': 'blah'}, 'time': ..., 'fields': {'instantaneous_power': 0, 'average_power': 0, 'left_power': -1, 'right_power': -1, 'torque': 0.0, 'angular_velocity': 0.0, 'cadence': 255}}
        """
        fields = {name: getattr(self, name) for name in self.__dataclass_fields__}

        for f in fields:
            if isinstance(fields[f], Enum):
                fields[f] = fields[f].value

        return {
            "measurement": type(self).__name__,
            "tags": tags,
            "time": int(
                datetime.datetime.utcnow()
                .replace(tzinfo=datetime.timezone.utc)
                .timestamp()
                * 1e9
            ),
            "fields": fields,
        }


@dataclass
class BatteryData:
    """Has it's own dataclass because there can be multiple instances of this in one device"""

    battery_id: int = 0
    voltage_fractional: float = field(default=0.0, metadata={"unit": "V"})
    voltage_coarse: int = field(default=0, metadata={"unit": "V"})
    status: BatteryStatus = BatteryStatus.Unknown
    operating_time: int = field(default=0, metadata={"unit": "seconds"})


@dataclass
class CommonData(DeviceData):
    """
    ANT+ common device data
    """

    manufacturer_id: int = 0xFFFF
    serial_no: int = 0xFFFFFFFF
    software_ver: str = ""
    hardware_rev: int = 0xFF
    model_no: int = 0xFFFF
    battery_number: int = 0xFF
    last_battery_id: int = (
        0xFF  # 0xFF is not used, otherwise 0:3 is battery number, 4:7 is ID
    )
    last_battery_data: BatteryData = field(
        default_factory=BatteryData
    )  # the last one recieved or only if last_battery_id = 0xFF
    timedate: Optional[datetime.datetime] = None

    def manufacturer_page_payload(self) -> List[int]:
        payload = [0x50, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]
        payload[3] = self.hardware_rev
        payload[4] = self.manufacturer_id & 0xFF
        payload[5] = (self.manufacturer_id >> 8) & 0xFF
        payload[6] = self.model_no & 0xFF
        payload[7] = (self.model_no >> 8) & 0xFF

        return payload

    def product_info_page_payload(self) -> List[int]:
        payload = [0x51, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]
        # TODO doesn't cover rev
        try:
            payload[3] = int(float(self.software_ver)) * 10
        except:
            payload[3] = 0x00
        payload[4:8] = self.serial_no.to_bytes(4, byteorder='little')

        return payload


class AntPlusDevice:
    """
    Base class to create ANT+ devices with. Handles attached state and common data pages in `_on_data`.

    When creating a class that inherits this, one should overload the `on_data` method for device specific data RX.

    Use `on_found` callback to do stuff when first found and `on_update` to act whenever new data arrives.
    """

    def __init__(
        self,
        node: Node,
        device_type: int,
        device_id: int = 0,
        period: int = 8070,
        rf_freq: int = 57,
        name: str = "unknown",
        trans_type: int = 0,
        master: bool = False,
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.period = period
        self.rf_freq = rf_freq
        # LSB is 0x05 for master
        if master and trans_type == 0:
            self.trans_type = 5
        else:
            self.trans_type = 0
        self.name = name
        self.master = master

        self._found = False
        self._attached = False
        self._page_count = 0 # for interleaving pages

        self.data = {
            "common": CommonData(),
            "batteries": [
                BatteryData() for _ in range(15)
            ],  # multi battery systems will update list with battery ID as index
        }

        self.node = node

        self.open_channel()

    def __str__(self):
        return f"{self.name}_{self.device_id:05}"

    @staticmethod
    def on_device_data(page: int, page_name: str, data: DeviceData):

        """Override this to capture device specific page data updates"""
        assert page
        assert page_name
        assert data
        pass

    def _on_update(self, data: list):
        self.on_update(data)

    @staticmethod
    def on_update(data: list):
        """Override this to capture raw data when recieved"""
        assert data
        pass

    def _on_found(self):
        self.on_found()

    @staticmethod
    def on_found():
        """Override this to do things when device is first found"""
        pass

    def _on_battery(self, data: BatteryData):
        _logger.info(
            f"Battery info {self}: ID: {self.data['common'].last_battery_id}; Fractional V: {self.data['common'].last_battery_data.voltage_fractional} V; Coarse V: {self.data['common'].last_battery_data.voltage_coarse} V; Status: {self.data['common'].last_battery_data.status}"
        )
        self.on_battery(data)

    @staticmethod
    def on_battery(data: BatteryData):
        """Override for updates of common battery page"""
        assert data
        pass

    def open_channel(self, extended=True, channel_type=None, ext_assign: Optional[int]=0x01):
        """Configures and opens the channel for the device on the Node"""
        if channel_type is None:
            channel_type = Channel.Type.BIDIRECTIONAL_RECEIVE if not self.master else Channel.Type.BIDIRECTIONAL_TRANSMIT

        self.channel = self.node.new_channel(
            channel_type, 0x00, ext_assign
        )

        # configure callbacks based on if slave or master device
        if not self.master:
            self.channel.on_broadcast_data = self._on_data
            self.channel.on_burst_data = self._on_data
            self.channel.on_acknowledge = self._on_data
            # only search timeout if slave as searching
            self.channel.set_search_timeout(0xFF)
        else:
            self.channel.on_broadcast_tx_data = self._on_tx_data
            self.channel.on_acknowledge_data = self._on_ack_data

        self.channel.set_id(self.device_id, self.device_type, self.trans_type)

        if extended:
            self.channel.enable_extended_messages(1)

        self.channel.set_period(self.period)
        self.channel.set_rf_freq(self.rf_freq)

        _logger.debug(f"opening {self.name} channel #{self.channel.id}, TYPE 0x{channel_type:02x} dID {self.device_id}; dType {self.device_type}; dTrans 0x{self.trans_type:02x} {self.rf_freq} @ {self.period} ms")
        self.channel.open()

    def close_channel(self):
        """Closes and removes the device channel on the Node"""
        self.node.remove_channel(self.channel)

    def request_dp(self, page: int = 71, no_times: int = 1):
        """
        Request datapage using the request page

        :param page int: datapage to request (default command status)
        """
        # init with byte 7 0x01 (request data page)
        data = [0x46, 0xFF, 0xFF, 0xFF, 0xFF, no_times & 0x7F, 0x00, 0x01]

        # serial no invalid for most
        data[1] = 0xFF
        data[2] = 0xFF

        # set the page
        data[6] = page & 0xFF

        self.send_acknowledged_data(data)

    def send_acknowledged_data(self, data: List[int]):
        """Attempt ack send but catches exception if fails: wrapper for send_acknowledged_data"""
        try:
            self.channel.send_acknowledged_data(data)
        except AntException as e:
            _logger.warning(f"Failed to get acknowledgement of TX page {data[0]}: {e}")

    def on_data(self, _):
        """Override this to capture raw data when recieved in child classes"""
        pass

    def _on_data(self, data):

        # extended (> 8) has the device number and id beyond page
        if len(data) > 8 and not self._attached:
            device_id = data[9] + (data[10] << 8)
            device_type = data[11]
            trans_type = data[12]

            # if device id was 0, this is first device so attach to it
            if self.device_id == 0:
                self.device_id = device_id
                self.trans_type = trans_type

                # set channel to this id
                self.channel.close()
                self.channel.set_id(self.device_id, self.device_type, self.trans_type)
                self.channel.open()

            elif self.device_id != device_id:
                raise RuntimeError(
                    "Device ID #{device_id} does not match ID channel was set to #{self.device_id}!"
                )

            _logger.info(
                f"Device ID #{device_id:05} of type {device_type}:{trans_type} attached: {self}"
            )

            # else device id was set and device is found so attached
            self._attached = True

        # fire on_found after we could have obtained ext device data
        if not self._found:
            self._found = True

            self.on_found()

        # % Common Pages %
        # manufacturer info
        if data[0] == 80:
            self.data["common"].hardware_rev = data[3]
            self.data["common"].manufacturer_id = data[4] + (data[5] << 8)
            self.data["common"].model_no = data[6] + (data[7] << 8)

            _logger.info(
                f"Manufacturer info {self}: HW Rev: {self.data['common'].hardware_rev}; ID: {self.data['common'].manufacturer_id}; Model: {self.data['common'].model_no}"
            )
        # product info
        elif data[0] == 81:
            sw_rev = data[2]
            sw_main = data[3]

            if sw_rev == 0xFF:
                self.data["common"].software_ver = str(sw_main / 10)
            else:
                self.data["common"].software_ver = str((sw_main * 100 + sw_rev) / 1000)

            self.data["common"].serial_no = int.from_bytes(
                data[4:8], byteorder="little"
            )

            _logger.info(
                f"Product info {self}: Software: {self.data['common'].software_ver}; Serial Number: {self.data['common'].serial_no}"
            )
        # battery status
        elif data[0] == 82:
            self.data["common"].last_battery_data.voltage_fractional = data[6] / 256
            self.data["common"].last_battery_data.voltage_coarse = data[7] & 0x0F
            self.data["common"].last_battery_data.status = BatteryStatus(
                (data[7] & 0x70) >> 4
            )
            self.data["common"].last_battery_data.battery_id = (data[2] & 0xF0) >> 4

            cumulative_resolution_bit = (data[7] & 0x80) == 0x80

            if cumulative_resolution_bit:
                self.data["common"].last_battery_data.operating_time = (
                    int.from_bytes(data[3:5], byteorder="little") * 2
                )
            else:
                self.data["common"].last_battery_data.operating_time = (
                    int.from_bytes(data[3:5], byteorder="little") * 16
                )

            # if system has multiple batteries to report, assign to index in batteries list
            if data[2] != 0xFF:
                self.data["common"].battery_number = data[2] & 0x0F
                self.data["common"].last_battery_id = (data[2] & 0xF0) >> 4
                # copy the dataclass to batteries list
                self.data["batteries"][
                    self.data["common"].last_battery_id
                ] = dataclasses.replace(self.data["common"].last_battery_data)
            # else not using ID so just report that as invalid and 1 battery
            else:
                self.data["common"].battery_number = 1
                self.data["common"].last_battery_id = data[2]

            self._on_battery(self.data["common"].last_battery_data)
        # date and time
        elif data[0] == 83:
            second = data[2]
            minute = data[3]
            hour = data[4]
            # day_of_month = (data[5] & 0xE0) >> 5 # bits 5-7
            day = data[5] & 0x1F  # bits 0-4
            month = data[6]
            year = data[7] + 2000

            self.data["common"].timedate = datetime.datetime(
                year, month, day, hour, minute, second
            )

        # run other pages for sub-classes
        self.on_data(data)

        # run user on_update after sub-class pages read
        self._on_update(data)

    def on_tx_data(self) -> Optional[List[int]]:
        """
        Override to add device specific TX pages, use self._page_count for page counter.

        Common pages are sent automatically.

        """
        pass

    def _on_tx_data(self, data):
        """Sends page data on EVENT_TX interval based on channel period"""
        # manufacturer’s identification
        if self._page_count == 0:
            payload = self.data["common"].manufacturer_page_payload()
        # product information
        elif self._page_count == 65:
            payload = self.data["common"].product_info_page_payload()
        # device specific
        else:
            payload = self.on_tx_data()

        if payload is not None:
            _logger.debug(f"Sending EVENT_TX #{self._page_count} payload {payload}")
            self.channel.send_broadcast_data(payload)

        if self._page_count == 129:
            self._page_count = 0
        else:
            self._page_count += 1

    def on_ack_data(self, data) -> Optional[List[int]]:
        """
        Override to act on broadcast ACK data recieved.

        Common page requests are replied automatically
        """
        assert data
        pass

    def _on_ack_data(self, data):
        """Replies to common page requests or forwards to `on_ack_data` callback"""
        page = data[0]

        if page == 80: # manufacturer
            payload = self.data["common"].manufacturer_page_payload()
        elif page == 81: # product
            payload = self.data["common"].product_info_page_payload()
        elif page == 82: # battery
            # TODO
            # payload = self.battery_status_page_payload()
            payload = None
        else:
            payload = self.on_ack_data(data)

        if payload is not None:
            self.channel.send_broadcast_data(payload)
