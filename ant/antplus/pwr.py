from .device import AntPlusDevice

import array
import logging

_logger = logging.getLogger("ant.antplus.PWR")

# bicycle power sensor
class PwrDevice(AntPlusDevice):
    CHANNEL_PERIOD = 8182
    DEVICE_TYPE = 11

    class Page:
        CALIBRATION = 0x01
        GET_SET_PARAMETERS = 0x02
        MEASUREMENT_OUTPUT = 0x03
        POWER_ONLY = 0x10
        TORQUE_AT_WHEEL = 0x11
        TORQUE_AT_CRANK = 0x12
        TORQUE_EFFECTIVENESS = 0x13
        CRANK_TORQUE_FREQUENCY = 0x20
        # cycling dynamics
        RIGHT_FORCE_ANGLE = 0xE0
        LEFT_FORCE_ANGLE = 0xE1
        PEDAL_POSITION = 0xE2

    class CalibrationID:
        MANUAL_ZERO_REQUEST = 0xAA
        AUTO_ZERO_CONFIG = 0xAB
        RESPONSE_SUCCESS = 0xAC
        RESPONSE_FAILED = 0xAF
        AUTO_ZERO_SUPPORT = 0x12
        # TODO complete

    def __init__(self, node, device_number, device_type, transmission_type):
        if device_type != PwrDevice.DEVICE_TYPE:
            # TODO : eigenlijk willen we hier een error genereren en een leeg object teruggeven
            print(
                f"Error, device_type = {device_type} is not a Combined Bicycle Speed/Cadence device!"
            )
            return
        channel_period = PwrDevice.CHANNEL_PERIOD

        super().__init__(
            node, device_number, device_type, transmission_type, channel_period
        )
        # specific init for the PWR device
        self.status["update_event_count"] = 0
        self.status["instant_cadence"] = 0
        self.status["instant_power"] = 0
        self.status["total_power"] = 0
        self.status["pedal_balance"] = 50

    def on_antplus_bcdata(self, data):
        # handle PWR specific pages here
        status = self.status
        if data[0] == PwrDevice.Page.POWER_ONLY:
            prev_event_count = status["update_event_count"]
            new_event_count = data[1]
            if new_event_count != prev_event_count:
                status["instant_power"] = int.from_bytes(data[6:8], byteorder="little")
                prev_total_power = status["total_power"]
                new_total_power_bytes = int.from_bytes(
                    data[4:6], byteorder="little"
                )  # in Watt
                if new_total_power_bytes < prev_total_power & 0xFFFF:  # rollover
                    status["total_power"] += 0xFFFF
                status["total_power"] = (
                    status["total_power"] & ~0xFFFF
                ) + new_total_power_bytes
                status["avg_power"] = (status["total_power"] - prev_total_power) / (
                    new_event_count - prev_event_count
                )
                if data[3] != 0xFF:
                    status["instant_cadence"] = data[3]  # in rpm
                if data[2] != 0xFF:
                    # TODO : improve this
                    self.status["pedal_balance"] = data[2] & 0x7F
                    self.status["pedal_contribution"] = data[2] >> 7
                status["update_event_count"] = new_event_count
        # TODO : one of these pages indicates support for auto-zero
        elif data[0] == PwrDevice.Page.TORQUE_AT_WHEEL:
            _logger.info(f"TORQUE_AT_WHEEL data (not implemented) : {data}")
        elif data[0] == PwrDevice.Page.TORQUE_AT_CRANK:
            _logger.info(f"TORQUE_AT_CRANK data (not implemented) : {data}")
        elif data[0] == PwrDevice.Page.TORQUE_EFFECTIVENESS:
            _logger.info(f"TORQUE_EFFECTIVENESS data (not implemented) : {data}")
        elif data[0] == PwrDevice.Page.CRANK_TORQUE_FREQUENCY:
            _logger.info(f"CRANK_TORQUE_FREQUENCY data (not implemented) : {data}")
        elif data[0] == PwrDevice.Page.CALIBRATION:
            _logger.info(f"CALIBRATION RESPONSE data : {data}")
            result = self.status["calibration_result"] = {}
            if data[1] == PwrDevice.CalibrationID.RESPONSE_SUCCESS:
                result["status"] = "success"
            elif data[1] == PwrDevice.CalibrationID.RESPONSE_FAILED:
                result["status"] = "failed"
            result["auto_zero_status"] = data[2]
            result["calibration_data"] = int.from_bytes(data[6:8], byteorder="little")
        elif data[0] == PwrDevice.Page.MEASUREMENT_OUTPUT:
            # provides raw system measurements during calibration, or a countdown
            _logger.info(f"MEASUREMENT_OUTPUT data : {data}")
            # TODO : decode data + maybe append this in status['calibration_result']

        else:
            pass

        # base class gets everything too, so it can handle the wait for page events
        super().on_antplus_bcdata(data)
        # notify callback or polling self.status?

    def start_calibration(self, status_callback=None):
        # TODO : why doesn't the function definition accept calibration_type=FECDevice.CalibrationType.SPIN_DOWN_CALIBRATION (default param)??
        _reserved = 0xFF
        if status_callback:
            self._calibration_status_callback = (
                status_callback  # replace the default callback
            )
        req_data = array.array(
            "B",
            [
                PwrDevice.Page.CALIBRATION,
                PwrDevice.CalibrationID.MANUAL_ZERO_REQUEST,
                _reserved,
                _reserved,
                _reserved,
                _reserved,
                _reserved,
                _reserved,
            ],
        )
        _logger.info(f"PWR:start_calibration:sending request data : {req_data}")
        self.channel.send_acknowledged_data(req_data)  # sync by channel.py

    # TODO : check, §16 device profile hints that requesting page 10 cancels the calibration?
    def stop_calibration(self):
        self._request_data_page(PwrDevice.Page.POWER_ONLY)
        self._wait_for_page_data(PwrDevice.Page.POWER_ONLY)

    # TODO : true/false : is this the same as 1/0 ?
    def set_auto_zero_configuration(self, on=1):
        _reserved = 0xFF
        req_data = array.array(
            "B",
            [
                PwrDevice.Page.CALIBRATION,
                PwrDevice.CalibrationID.AUTO_ZERO_CONFIG,
                on,
                _reserved,
                _reserved,
                _reserved,
                _reserved,
                _reserved,
            ],
        )
        _logger.info(
            f"PWR:set_auto_zero_configuration:sending request data : {req_data}"
        )
        self.channel.send_acknowledged_data(req_data)  # sync by channel.py
        # this doesn't perform a calibration, but we should be able to learn if the sensor supports auto-zero
        # TODO : wait for response on page PwrDevice.Page.CALIBRATION?

    # TODO : improve intf
    # subpage = type of parameter requested (crank parameters, ...)
    # 0x01 : CRANK_PARAMETERS
    # 0x02 : POWER_PHASE_CONFIGURATION
    # 0x04 : RIDER_POSITION
    # 0xFD : advanced capabilities 1
    # 0xFE : advanced capabilities 2
    def get_parameters(self, subpage):
        self._request_data_page(PwrDevice.Page.GET_SET_PARAMETERS, [subpage, 0xFF])
        # TODO: we will timeout here if the sensor doesn't support this page
        resp_data = self._wait_for_page_data(PwrDevice.Page.GET_SET_PARAMETERS)
        _logger.info(f"PWR:get_parameters:got data : {resp_data}")
        # TODO decode resp_data (device profile §15.2)

    def _calibration_status_callback(self, status):
        # the default callback for calibration status updates
        _logger.info(f"PWR:calibration status : {status}")
