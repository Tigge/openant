"""
Drivers to get data from an ANT capable device
"""
# Ant
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import logging
from typing import Generator, Optional
from enum import Enum

from usb.core import Device

_logger = logging.getLogger("openant.base.driver")


class StandardOptions(Enum):
    NoRxChannels = 0
    NoTxChannels = 1
    NoRxMessages = 2
    NoTxMessages = 3
    NoAckMessages = 4
    NoBurstMessages = 5
    Reserved = 6

    @staticmethod
    def from_byte(byte: int):
        ret = set()
        for i in range(StandardOptions.Reserved.value):
            if byte >> i & 0x01:
                ret.add(StandardOptions(i))
        return ret

    @classmethod
    def _missing_(cls, _):
        return StandardOptions.Reserved


class AdvancedOptions(Enum):
    NetworkEnabled = 0
    SerialNumberEnabled = 3
    PerChannelTxPowerEnabled = 4
    LowPrioritySearchNEnabled = 5
    ScriptEnabled = 6
    SearchListEnabled = 7
    Reserved = 8

    @staticmethod
    def from_byte(byte: int):
        ret = set()
        for i in range(AdvancedOptions.Reserved.value):
            if byte >> i & 0x01:
                ret.add(AdvancedOptions(i))
        return ret

    @classmethod
    def _missing_(cls, _):
        return AdvancedOptions.Reserved


class AdvancedOptionsTwo(Enum):
    LedEnabled = 0
    ExtMessageEnabled = 1
    ScanModeEnabled = 2
    ProximitySearchEnabled = 4
    ExtAssignEnabled = 5
    FsAntFsEnabled = 6
    Fit1Enabled = 7
    Reserved = 8

    @staticmethod
    def from_byte(byte: int):
        ret = set()
        for i in range(AdvancedOptionsTwo.Reserved.value):
            if byte >> i & 0x01:
                ret.add(AdvancedOptionsTwo(i))
        return ret

    @classmethod
    def _missing_(cls, _):
        return AdvancedOptionsTwo.Reserved


class AdvancedOptionsThree(Enum):
    AdvancedBurstEnabled = 0
    EventBufferingEnabled = 0
    EventFilteringEnabled = 1
    HighDutySearchEnabled = 2
    SearchSharingEnabled = 4
    SelectiveDataUpdateEnabled = 6
    EncryptedChannelEnabled = 7
    Reserved = 8

    @staticmethod
    def from_byte(byte: int):
        ret = set()
        for i in range(AdvancedOptionsThree.Reserved.value):
            if byte >> i & 0x01:
                ret.add(AdvancedOptionsThree(i))
        return ret

    @classmethod
    def _missing_(cls, _):
        return AdvancedOptionsThree.Reserved


class DriverException(Exception):
    pass


class DriverNotFound(DriverException):
    pass


class DriverTimeoutException(DriverException):
    pass


class Driver:
    """Use as parent class to create ANT driver, compatiable with `Ant` class"""

    @classmethod
    def find(cls):
        pass

    def open(self):
        pass

    def close(self):
        pass

    def read(self):
        pass

    def write(self, data):
        pass


drivers = []

try:
    import array
    import os
    import os.path

    import serial

    class SerialDriver(Driver):
        """CDC serial ANT device"""

        ID_VENDOR = 0x0FCF
        ID_PRODUCT = 0x1004

        @classmethod
        def find(cls):
            return cls.get_url() is not None

        @classmethod
        def get_url(cls):
            try:
                path = "/sys/bus/usb-serial/devices"
                for device in os.listdir(path):
                    try:
                        device_path = os.path.realpath(os.path.join(path, device))
                        device_path = os.path.join(device_path, "../../")
                        ven = int(
                            open(os.path.join(device_path, "idVendor")).read().strip(),
                            16,
                        )
                        pro = int(
                            open(os.path.join(device_path, "idProduct")).read().strip(),
                            16,
                        )
                        if ven == cls.ID_VENDOR or cls.ID_PRODUCT == pro:
                            return os.path.join("/dev", device)
                    except:
                        continue
                return None
            except OSError:
                return None

        def open(self):
            # TODO find correct port on our own, could be done with
            # serial.tools.list_ports, but that seems to have some
            # problems at the moment.

            try:
                self._serial = serial.serial_for_url(self.get_url(), 115200)
            except serial.SerialException as e:
                raise DriverException(e)

            _logger.debug("Serial information:")
            _logger.debug("name:            ", self._serial.name)
            _logger.debug("port:            ", self._serial.port)
            _logger.debug("baudrate:        ", self._serial.baudrate)
            _logger.debug("bytesize:        ", self._serial.bytesize)
            _logger.debug("parity:          ", self._serial.parity)
            _logger.debug("stopbits:        ", self._serial.stopbits)
            _logger.debug("timeout:         ", self._serial.timeout)
            _logger.debug("writeTimeout:    ", self._serial.writeTimeout)
            _logger.debug("xonxoff:         ", self._serial.xonxoff)
            _logger.debug("rtscts:          ", self._serial.rtscts)
            _logger.debug("dsrdtr:          ", self._serial.dsrdtr)
            _logger.debug("interCharTimeout:", self._serial.interCharTimeout)

            self._serial.timeout = 0

        def read(self):
            data = self._serial.read(4096)
            # print "serial read", len(data), type(data), data
            return array.array("B", data)

        def write(self, data):
            try:
                # print "serial write", type(data), data
                self._serial.write(data)
            except serial.SerialTimeoutException as e:
                raise DriverTimeoutException(e) from e

        def close(self):
            self._serial.close()

    drivers.append(SerialDriver)

except ImportError:
    pass

try:
    import usb.core
    import usb.util
    from .commons import is_windows
    import time

    class USBDriver(Driver):
        """
        Parent USBDriver class - overwrite and replace ID_VENDOR, ID_PRODUCT for the VID/PID of Dynastream compatiable device
        """

        # default USB2
        ID_VENDOR = 0x0FCF
        ID_PRODUCT = 0x1008

        def __init__(self):
            self.dev: Optional[Generator[Device, None, None]] = None
            self._in = None
            self._out = None

        @classmethod
        def find(cls):
            return (
                usb.core.find(idVendor=cls.ID_VENDOR, idProduct=cls.ID_PRODUCT)
                is not None
            )

        def open(self):
            # Find USB device
            _logger.debug(
                "USB Find device, vendor %#04x, product %#04x",
                self.ID_VENDOR,
                self.ID_PRODUCT,
            )
            self.dev = usb.core.find(idVendor=self.ID_VENDOR, idProduct=self.ID_PRODUCT)

            # was it found?
            if self.dev is None:
                raise ValueError("Device not found")

            _logger.debug("USB Config values:")
            for cfg in self.dev:
                _logger.debug(" Config %s", cfg.bConfigurationValue)
                for intf in cfg:
                    _logger.debug(
                        "  Interface %s, Alt %s",
                        str(intf.bInterfaceNumber),
                        str(intf.bAlternateSetting),
                    )
                    for ep in intf:
                        _logger.debug("   Endpoint %s", str(ep.bEndpointAddress))

            # unmount a kernel driver (TODO: should probably reattach later)
            try:
                if self.dev.is_kernel_driver_active(0):
                    _logger.debug("A kernel driver active, detatching")
                    self.dev.detach_kernel_driver(0)
                else:
                    _logger.debug("No kernel driver active")
            except NotImplementedError as e:
                _logger.warning(
                    "Could not check if kernel driver was active, not implemented in usb backend"
                )

            # set the active configuration. With no arguments, the first
            # configuration will be the active one
            self.dev.set_configuration()
            try:
                self.dev.reset()
            except NotImplementedError as _:
                _logger.warning(
                    "Could not reset the device, not implemented in usb backend"
                )
            if is_windows():
                time.sleep(2)

            # get an endpoint instance
            cfg = self.dev.get_active_configuration()
            intf = cfg[(0, 0)]

            self._out = usb.util.find_descriptor(
                intf,
                # match the first OUT endpoint
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_OUT,
            )

            _logger.debug(
                "USB Endpoint out: %s, %s", self._out, self._out.bEndpointAddress
            )

            self._in = usb.util.find_descriptor(
                intf,
                # match the first OUT endpoint
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_IN,
            )

            _logger.debug(
                "USB Endpoint in: %s, %s", self._in, self._in.bEndpointAddress
            )

            assert self._out is not None and self._in is not None

        def close(self):
            usb.util.dispose_resources(self.dev)
            try:
                if self.dev is not None:
                    self.dev.attach_kernel_driver(0)
            except NotImplementedError as e:
                _logger.warning(
                    "Could not re-attach kernel driver, not implemented in usb backend"
                )
            _logger.debug("usbdriver.closed")
            pass

        def read(self):
            return self._in.read(4096)

        def write(self, data):
            self._out.write(data)

    class USB2Driver(USBDriver):
        """ANTUSB2 stick: http://www.thisisant.com/developer/components/antusb2/"""

        ID_VENDOR = 0x0FCF
        ID_PRODUCT = 0x1008

    class USB3Driver(USBDriver):
        """ANTUSB-m stick: http://www.thisisant.com/developer/components/antusb-m/"""

        ID_VENDOR = 0x0FCF
        ID_PRODUCT = 0x1009

    drivers.append(USB2Driver)
    drivers.append(USB3Driver)

except ImportError:
    pass


def find_driver():
    """
    Auto-find avialable driver

    :raises DriverNotFound: unable to find any compatiable drivers
    """
    _logger.info(f"Drivers available: {drivers}")

    for driver in reversed(drivers):
        if driver.find():
            _logger.info(f"Using driver: {driver}")
            return driver()
    raise DriverNotFound
