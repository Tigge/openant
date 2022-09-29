import datetime
import array
import datetime
import logging
from typing import Optional

from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.easy.exception import AntException

from dataclasses import dataclass, field
from enum import Enum

_logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """
    ANT+ device profile identifiers
    """
    Unknown = 255
    PowerMeter = 11
    FitnessEquipment = 17
    ControllableDevice = 16
    BloodPressure = 18
    Geocache = 19
    Environment = 25
    TirePressureMonitor = 48
    WeightScale = 119
    Heartrate = 120
    BikeSpeedCadence = 121
    BikeCadence = 122
    BikeSpeed = 123
    StrideSpeed = 124
    Lev = 20
    Radar = 40
    Shifting = 34

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
        fields = {name: getattr(self, name) for name in self.__dataclass_fields__}

        for f in fields:
            if isinstance(fields[f], Enum):
                fields[f] = fields[f].value

        return {
            "measurement": type(self).__name__,
            "tags": tags,
            "time": int(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp() * 1e9),
            "fields": fields,
        }

@dataclass
class BatteryData():
    """
    Has it's own dataclass because there can be multiple instances of this in one device
    """
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
    serial_no: int = 0xFFFF
    software_ver: str = ''
    hardware_rev: int = 0xFF
    model_no: int = 0xFFFF
    last_battery_id: int = 0xFF # 0xFF is not used, otherwise 0:3 is battery number, 4:7 is ID
    last_battery_data: BatteryData = BatteryData() # the last one recieved or only if last_battery_id = 0xFF
    timedate: Optional[datetime.datetime] = None

class AntPlusDevice(object):
    """
    Base class to create ANT+ devices with. Handles attached state and common data pages in `_on_data`.

    When creating a class that inherits this, one should overload the `on_data` method for device specific data RX.

    Use `on_found` callback to do stuff when first found and `on_update` to act whenever new data arrives.
    """

    def __init__(self, node: Node, device_type:int, device_id:int=0, period:int=8070, rf_freq:int=57, name:str="unknown", trans_type:int=0):
        self.device_id = device_id
        self.device_type = device_type
        self.period = period
        self.rf_freq = rf_freq
        self.trans_type = trans_type
        self.name = name

        self._found = False
        self._attached = False

        self.data = {
            'common': CommonData(),
            'batteries': [BatteryData() for _ in range(15)] # multi battery systems will update list with battery ID as index
        }

        self.node = node

        self.open_channel()

    def __str__(self):
        return f"{self.name}_{self.device_id:05}"

    @staticmethod
    def on_device_data(page: int, page_name: str, data: dict):
        """Override this to capture device specific page data updates"""
        assert page
        assert page_name
        assert data
        pass

    @staticmethod
    def on_update(data: list):
        """Override this to capture raw data when recieved"""
        assert data
        pass

    @staticmethod
    def on_found():
        """Override this to do things when device is first found"""
        pass

    @staticmethod
    def on_battery(data: BatteryData):
        """Override for updates of common battery page"""
        assert data
        pass

    def open_channel(self):
        self.channel = self.node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE, 0x00, 0x01)

        self.channel.on_broadcast_data = self._on_data
        self.channel.on_burst_data = self._on_data
        self.channel.on_acknowledge = self._on_data

        # setup slave channel
        self.channel.set_id(self.device_id, self.device_type, self.trans_type)
        self.channel.enable_extended_messages(1)

        self.channel.set_search_timeout(0xFF)
        self.channel.set_period(self.period)
        self.channel.set_rf_freq(self.rf_freq)

        self.channel.open()

    def close_channel(self):
        self.channel.close()

    def request_dp(self, page: int = 71):
        """
        Request datapage using the request page

        :param page int: datapage to request (default command status)
        """
        # init with byte 7 0x01 (request data page)
        data = array.array("B", [0x46, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x01])

        # serial no invalid for most
        data[1] = 0xFF
        data[2] = 0xFF

        # set the page
        data[6] = page & 0xFF

        self.send_acknowledged_data(data)

    def send_acknowledged_data(self, data: array.array):
        """
        Attempt ack send but catches exception if fails: wrapper for send_acknowledged_data
        """
        try:
            self.channel.send_acknowledged_data(data)
        except AntException as e:
            _logger.warning(f"Failed to get acknowledgement of TX page {data[0]}: {e}")

    def on_data(self, _):
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
                raise RuntimeError("Device ID #{device_id} does not match ID channel was set to #{self.device_id}!")

            _logger.info(f"Device ID #{device_id:05} of type {device_type}:{trans_type} attached: {self}")

            # else device id was set and device is found so attached
            self._attached = True

        # fire on_found after we could have obtained ext device data
        if not self._found:
            self._found = True

            self.on_found()

        # % Common Pages %
        # manufacturer info
        if data[0] == 80:
            self.data['common'].hardware_rev = data[3]
            self.data['common'].manufacturer_id = data[4] + (data[5] << 8)
            self.data['common'].model_no = data[6] + (data[7] << 8)

            _logger.info(f"Manufacturer info {self}: HW Rev: {self.data['common'].hardware_rev}; ID: {self.data['common'].manufacturer_id}; Model: {self.data['common'].model_no}")
        # product info
        elif data[0] == 81:
            sw_rev = data[2]
            sw_main = data[3]

            if sw_rev == 0xFF:
                self.data['common'].software_ver = str(sw_main / 10)
            else:
                self.data['common'].software_ver = str((sw_main * 100 + sw_rev) / 1000)

            self.data['common'].serial_no = int.from_bytes(data[4:8], byteorder='little')

            _logger.info(f"Product info {self}: Software: {self.data['common'].software_ver}; Serial Number: {self.data['common'].serial_no}")
        # battery status
        elif data[0] == 82:
            self.data['common'].last_battery_data.voltage_fractional = data[6] / 256
            self.data['common'].last_battery_data.voltage_coarse = data[7] & 0x0F
            self.data['common'].last_battery_data.status = BatteryStatus(data[7] & 0x70)

            cumulative_resolution_bit = (data[7] & 0x80) == 0x80

            if cumulative_resolution_bit:
                self.data['common'].last_battery_data.operating_time = int.from_bytes(data[3:5], byteorder='little') * 2
            else:
                self.data['common'].last_battery_data.operating_time = int.from_bytes(data[3:5], byteorder='little') * 16

            # if system has multiple batteries to report, assign to index in batteries list
            if (data[2] != 0xFF):
                self.data['common'].battery_number = data[2] & 0x0F
                self.data['common'].last_battery_id = data[2] & 0xF0
                self.data['batteries'][self.data['common'].last_battery_id] = self.data['common'].last_battery_data.copy()
            # else not using ID so just report that as invalid and 1 battery
            else:
                self.data['common'].battery_number = 1
                self.data['common'].last_battery_id = data[2]

            _logger.info(f"Battery info {self}: ID: {self.data['common'].last_battery_id}; Fractional V: {self.data['common'].last_battery_data.voltage_fractional} V; Coarse V: {self.data['common'].last_battery_data.voltage_coarse} V; Status: {self.data['common'].last_battery_data.status}")

            self.on_battery(self.data['common'].last_battery_data)
        # date and time
        elif data[0] == 83:
            second = data[2]
            minute = data[3]
            hour = data[4]
            # day_of_month = (data[5] & 0xE0) >> 4 # bits 5-7
            day = data[5] & 0x1F # bits 4-0
            month = data[6]
            year = data[7] + 2000

            self.data['common'].timedate = datetime.datetime(year, month, day, hour, minute, second)

        # run other pages for sub-classes
        self.on_data(data)

        # run user on_update after sub-class pages read
        self.on_update(data)