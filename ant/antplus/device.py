from __future__ import absolute_import, print_function

from ant.easy.channel import Channel

import logging
import threading
import array  # TODO : dit kan beter!

_logger = logging.getLogger("ant.antplus.device")


class AntPlusDevice:
    class Page:
        # common data pages
        REQUEST_DATA = 70
        COMMAND_STATUS = 71
        GENERIC_COMMAND = 73
        # TODO complete
        MANUFACTURER_INFO = 80
        PRODUCT_INFO = 81
        BATTERY_STATUS = 82
        TIME_AND_DATE = 83
        SUBFIELD_DATA = 84
        MEMORY_LEVEL = 85
        PAIRED_DEVICES = 86
        ERROR_DESCRIPTION = 87

    def __init__(
        self, node, device_number, device_type, transmission_type, channel_period
    ):
        self.device_number = device_number
        self.device_type = device_type
        self.transmission_type = transmission_type
        self.channel_period = channel_period
        self.info = {}
        self.status = {"print_cnt": 1}
        self.node = node
        self._event_wait = threading.Event()
        self._pagenum_to_wait_for = -1
        self._page_data = []  # for returning page data to a blocked request thread

        # setup our channel to the device
        self.channel = self.node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
        self.channel.on_broadcast_data = self.on_antplus_bcdata
        self.channel.on_acknowledge = self.on_antplus_ackdata
        self.channel.set_id(
            self.device_number, self.device_type, self.transmission_type
        )
        # channel.enable_extended_messages(0) #zonder deze lijn krijg je default extended msg omdat bgchannel extended heeft ??
        self.channel.set_search_timeout(30)  # in seconds
        self.channel.set_period(
            self.channel_period
        )  # std waarde uit de <> std profiles
        self.channel.set_rf_freq(57)
        self.channel.open()

    def close(self):
        self.channel.close()

    def on_antplus_ackdata(self, data):
        _logger.info(f"{self.device_number}/{self.device_type} ack data : {data}")

    def on_antplus_bcdata(self, data):
        if (
            data[0] == AntPlusDevice.Page.MANUFACTURER_INFO
        ):  # manufacturer's information
            self.info["hardware_revision"] = data[3]
            self.info["manufacturer_id"] = int.from_bytes(data[4:6], byteorder="little")
            self.info["model_number"] = int.from_bytes(data[6:8], byteorder="little")
        elif data[0] == AntPlusDevice.Page.PRODUCT_INFO:  # product information
            supplimental_sw_revision = data[2]
            if data[2] == 0xFF:
                supplimental_sw_revision = 0
            self.info["software_revision"] = (
                100.0 * data[3] + supplimental_sw_revision
            ) / 1000.0  # float
            self.info["serial_number"] = int.from_bytes(data[4:8], byteorder="little")
        elif data[0] in [AntPlusDevice.Page.BATTERY_STATUS]:
            # TODO !  (see info PWR device profile)
            self.status["battery_status"] = "to_be_implemented"
            pass
        elif data[0] in [AntPlusDevice.Page.COMMAND_STATUS]:
            # to be handled by specific device
            pass
        else:
            pass

        pagenum = data[0]
        if self._pagenum_to_wait_for != -1 and self._pagenum_to_wait_for == pagenum:
            self._page_data = data
            self._event_wait.set()

        # TODO : cleanup temporary if
        if self.status["print_cnt"] > 0:
            _logger.info(f"{self.device_number}/{self.device_type} bc data : {data}")
            self.status["print_cnt"] -= 1

    def _wait_for_page_data(self, page_num):
        self._pagenum_to_wait_for = page_num
        self._event_wait.wait(5.0)  # 5 seconds timeout
        # when we are here the on_antplus_data callback will have delivered the data
        # TODO handle timeout
        if not self._event_wait.is_set():
            _logger.warning(f"timeout waiting for page {page_num} data")
        self._event_wait.clear()
        self._pagenum_to_wait_for = -1
        return self._page_data

    def _request_data_page_ack(self, page_num, descriptor_bytes=[0xFF, 0xFF]):
        transmit_until_ack = 0x80
        command_type = 0x1  # slave request data page
        _unused = 0xFF
        req_data = array.array(
            "B",
            [
                AntPlusDevice.Page.REQUEST_DATA,
                _unused,
                _unused,
                descriptor_bytes[0],
                descriptor_bytes[1],
                transmit_until_ack,
                page_num,
                command_type,
            ],
        )
        _logger.info(f"sending request data : {req_data}")
        self.status["print_cnt"] = 20  # let's print the next 20 bc msgs
        self.channel.send_acknowledged_data(
            req_data
        )  # dit gaat blocken tot EVENT_TRANSFER_TX_COMPLETED
        # we hebben hier ook al een timeout exception gekregen via filter.py line 61 --> TODO : catch!
        return

    def _request_data_page(self, page_num, descriptor_bytes=[0xFF, 0xFF]):
        number_of_transmits = 3
        command_type = 0x1  # slave request data page
        _unused = 0xFF
        req_data = array.array(
            "B",
            [
                AntPlusDevice.Page.REQUEST_DATA,
                _unused,
                _unused,
                descriptor_bytes[0],
                descriptor_bytes[1],
                number_of_transmits,
                page_num,
                command_type,
            ],
        )
        _logger.info(f"sending request data : {req_data}")
        self.status["print_cnt"] = 20  # let's print the next 20 bc msgs
        try:
            self.channel.send_acknowledged_data(
                req_data
            )  # dit gaat blocken tot EVENT_TRANSFER_TX_COMPLETED
        except:
            # TODO : hoe kunnen we de specifieke AntException opvangen??
            _logger.warning("timeout waiting for TX_COMPLETED event!")
        return

    def get_manufacturer_info(self):
        if not "hardware_revision" in self.info:
            self._request_data_page(AntPlusDevice.Page.MANUFACTURER_INFO)
            page_data = self._wait_for_page_data(AntPlusDevice.Page.MANUFACTURER_INFO)
            _logger.info(f"got manufacturer info :  {page_data}")

        # the data are now stored under self.info
        return {
            "hardware_revision": self.info["hardware_revision"],
            "manufacturer_id": self.info["manufacturer_id"],
            "model_number": self.info["model_number"],
        }

    def get_product_info(self):
        if not "serial_number" in self.info:
            self._request_data_page(AntPlusDevice.Page.PRODUCT_INFO)
            page_data = self._wait_for_page_data(AntPlusDevice.Page.PRODUCT_INFO)
            _logger.info(f"got product info :  {page_data}")

        # the data are now stored under self.info
        return {
            "serial_number": self.info["serial_number"],
            "software_revision": self.info["software_revision"],
        }

    # TODO : if no response (eg. not supported), timeout exception will occur
    # and self.info['battery_status'] does not exist
    def get_battery_status(self):
        if not "battery_status" in self.info:
            self._request_data_page(AntPlusDevice.Page.BATTERY_STATUS)
            page_data = self._wait_for_page_data(AntPlusDevice.Page.BATTERY_STATUS)
            _logger.info(f"got battery status info :  {page_data}")

        # the data are now stored under self.status
        return {"battery_status": self.info.get(["battery_status"], None)}

    def get_command_status(self):
        self._request_data_page(AntPlusDevice.Page.COMMAND_STATUS)
        page_data = self._wait_for_page_data(AntPlusDevice.Page.COMMAND_STATUS)
        status = {}
        status["last_cmd_id"] = page_data[1]
        status["cmd_sequence_nr"] = page_data[2]
        status["cmd_status"] = page_data[3]
        status["cmd_data"] = page_data[4:8]
        return status
