from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.base.message import Message
from .device import AntPlusDevice

import logging
import struct
import threading
import sys

import array # TODO : dit kan beter!

_logger = logging.getLogger("ant.antplus.FE-C")

class FECDevice(AntPlusDevice):
    FEC_CHANNEL_PERIOD = 8192
    FEC_DEVICE_TYPE = 17

    class Page:
        CALIBRATION_REQUEST_RESPONSE = 1
        CALIBRATION_PROGRESS = 2
        GENERAL_FE_DATA = 16
        GENERAL_SETTINGS = 17
        GENERAL_FE_METABOLIC_DATA = 18
        # TODO complete
        SPECIFIC_TRAINER_STATIONARY_BIKE_DATA = 25
        CONTROL_BASIC_RESISTANCE = 48
        CONTROL_TARGET_POWER = 49
        CONTROL_WIND_RESISTANCE = 50
        CONTROL_TRACK_RESISTANCE = 51
        FE_CAPABILITIES = 54
        USER_CONFIG = 55
    
    class CalibrationType:
        ZERO_OFFSET_CALIBRATION = 0x40
        SPIN_DOWN_CALIBRATION = 0x80
        CANCEL = 0
    
    def __init__(self, node, device_number, device_type, transmission_type):
        if device_type != FECDevice.FEC_DEVICE_TYPE:
            # TODO : eigenlijk willen we hier een error genereren en een leeg object teruggeven
            print(f"Error, device_type = {device_type} is not a FE-C device!")
            return
        channel_period = FECDevice.FEC_CHANNEL_PERIOD # device profile standard # TODO : cleanup magic numbers
        
        super().__init__(node, device_number, device_type, transmission_type, channel_period)
        # specific init for the FE-C device
        self.status['elapsed_time'] = 0.0 #seconds
        self.status['distance_traveled'] = 0 # meters
        self.status['lap_events'] = 0
        self.status['cur_resistance'] = None
        self.status['set_resistance'] = None
        self.status['set_target_power'] = None

        bikedata = self.bikedata = {}
        bikedata['update_event_count'] = 0
        bikedata['instant_cadence'] = 0
        bikedata['instant_power'] = 0
        bikedata['total_power'] = 0
        self.user = {}

    def on_antplus_bcdata(self, data):
        # handle FE-C specific pages here
        if data[0] == FECDevice.Page.GENERAL_FE_DATA:
            self.info['equipment_type'] = data[1] & 0xF # store with .info (static data)
            self.info['p16_capabilities'] = data[7] & 0xF # store with .info (static data)
            # elapsed_time (in s)
            # TODO : add moving_time : only count time in fe_state == 3 (IN_USE)
            elapsed_time_int = int (self.status['elapsed_time'] * 4.0)
            self.status['elapsed_time'] = 0.25*((elapsed_time_int & ~0xFF) + data[2])
            if data[2] < (elapsed_time_int & 0xFF): #rollover happened
                self.status['elapsed_time'] += 64.0  
            # distance_traveled (in m)
            if data[3] < (self.status['distance_traveled'] & 0xFF): #rollover happened
                self.status['distance_traveled'] += 256
            self.status['distance_traveled'] = (self.status['distance_traveled'] & ~0xFF) + data[3]
            # instantaneous speed (in m/s)
            instant_speed_value = int.from_bytes(data[4:6],byteorder='little')
            if instant_speed_value != 0xFFFF:
                self.status['instant_speed'] = 0.001 * instant_speed_value
            # heart rate
            if data[6] != 0xFF:
                self.status['heart_rate'] = data[6] # in bpm
            # status bitfield
            # direto : initially fe_state = 2, when moving fe_state=3, when stopped fe_state=4 & after +- 1 min fe_state=2
            fe_state = data[7] >> 4
            self.status['fe_state'] = fe_state & 0x7 # 0=reserved, 1=asleep, 2=ready, 3=in_use, 4=finished/paused
            lap_toggle_bit = (fe_state >> 3) & 0x1
            if lap_toggle_bit != self.status.get('lap_toggle_bit',0): # new lap event
                self.status['lap_events'] += 1
                self.status['lap_toggle_bit'] = lap_toggle_bit

        elif data[0] == FECDevice.Page.GENERAL_SETTINGS:
            if data[3] != 0xFF:
                self.status['cycle_length'] = data[3]
            incline = int.from_bytes(data[4:6],byteorder='little')
            if incline != 0xFFFF:
                self.status['cur_incline'] = 0.01*incline # signed in %
            self.status['cur_resistance'] = data[6] # in 0.5%
            # status bitfield (same as page 16)
            fe_state = data[7] >> 4
            self.status['fe_state'] = fe_state & 0x7 # 0=reserved, 1=asleep, 2=ready, 3=in_use, 4=finished/paused
            lap_toggle_bit = (fe_state >> 3) & 0x1
            if lap_toggle_bit != self.status.get('lap_toggle_bit',0): # new lap event
                self.status['lap_events'] += 1
                self.status['lap_toggle_bit'] = lap_toggle_bit

        elif data[0] == FECDevice.Page.SPECIFIC_TRAINER_STATIONARY_BIKE_DATA:
            bikedata = self.bikedata
            if bikedata['update_event_count'] != data[1]:
                # new event data
                prev_event_count = bikedata['update_event_count']
                new_event_count = data[1]
                prev_total_power = bikedata['total_power']
                new_total_power = int.from_bytes(data[3:5],byteorder='little') & 0x7FF # in Watt
                avg_power = (new_total_power - prev_total_power)/(new_event_count-prev_event_count)
                if data[2] != 0xFF:
                    bikedata['instant_cadence'] = data[2] # in rpm
                instant_power_value = int.from_bytes(data[5:7],byteorder='little') & 0x7FF
                if instant_power_value != 0xFFF:
                    bikedata['instant_power'] = instant_power_value # in Watt
                    bikedata['total_power'] = new_total_power # in Watt
                bikedata['avg_power'] = avg_power
                bikedata['trainer_status'] = (data[6] >> 4) & 0xF # calibration required / user config required
                bikedata['trainer_flags'] = data[7] & 0x3 # target power limits
                # status bitfield (same as page 16)
                fe_state = data[7] >> 4
                self.status['fe_state'] = fe_state & 0x7 # 0=reserved, 1=asleep, 2=ready, 3=in_use, 4=finished/paused
                lap_toggle_bit = (fe_state >> 3) & 0x1
                if lap_toggle_bit != self.status.get('lap_toggle_bit',0): # new lap event
                    self.status['lap_events'] += 1
                    self.status['lap_toggle_bit'] = lap_toggle_bit
                bikedata['update_event_count'] = new_event_count
        
        elif data[0] == FECDevice.Page.CALIBRATION_REQUEST_RESPONSE:
            _logger.info(f"CALIBRATION_REQUEST_RESPONSE : {data}")
            # receive result of a calibration
            resp = {}
            status = data[1]
            zero_offset_calibration_status = (status >> 6) & 0x1
            spindown_calibration_status = (status >> 7) & 0x1
            resp['zero_offset_calibration_success'] = zero_offset_calibration_status
            resp['spindown_calibration_success'] = spindown_calibration_status
            resp['temperature'] = data[3]
            resp['zero_offset'] = int.from_bytes(data[4:6],byteorder='little')
            resp['spindown_time'] = int.from_bytes(data[6:8],byteorder='little')

            #call callback
            self._calibration_status_callback(resp)

        elif data[0] == FECDevice.Page.USER_CONFIG:
            _logger.info(f"USER_CONFIG data : {data}")
            user = self.user
            # defaults from FE-C profile
            user['user_weight_kg'] = 75.0
            user['bicycle_wheel_diameter_in_mm'] = 700
            user['bicycle_weight_kg'] = 10.0
            user_weight = int.from_bytes(data[1:3],byteorder='little')
            if user_weight != 0xFFFF:
                user['user_weight_kg'] = 0.01*user_weight # kg
            if data[6] != 0xFF :
                user['bicycle_wheel_diameter_in_mm'] = 10*data[6] + (data[4] & 0xF)
            bike_weight = (data[5] << 4) + (data[4] >> 4)
            if bike_weight != 0xFFF:
                user['bicycle_weight_kg'] = 0.05*bike_weight # kg
            user['gear_ratio'] = 0.03*data[7]

        elif data[0] == FECDevice.Page.FE_CAPABILITIES:
            max_resistance = int.from_bytes(data[5:7],byteorder='little')
            if max_resistance != 0xFFFF:
                self.info['maximum_resistance'] = int.from_bytes(data[5:7],byteorder='little')
            self.info['p54_capabilities'] = data[7]

        elif data[0] in [FECDevice.Page.GENERAL_FE_METABOLIC_DATA]:
            # do nothing or not implemented
            pass

        elif data[0] == FECDevice.Page.CALIBRATION_PROGRESS:
            _logger.info(f"CALIBRATION_PROGRESS : {data}")
            # calibration progress update
            progress = {}
            # status
            status_txts = ['Not Requested','Pending']
            status = data[1]
            zero_offset_calibration_status = (status >> 6) & 0x1
            spindown_calibration_status = (status >> 7) & 0x1
            progress['zero_offset_calibration_status_txt'] = 'Zero Offset Calibration :' + status_txts[zero_offset_calibration_status]
            progress['spindown_calibration_status_txt'] = 'Spin-down Calibration :' + status_txts[spindown_calibration_status]
            #conditions
            conditions = data[2]
            condition_txts = ['Not Applicable', 'too low', 'OK', 'too high']
            temperature_condition = (conditions >> 4) & 0x3
            speed_condition = (conditions >> 6) & 0x3
            progress['temperature_condition_txt'] = 'Temperature : ' + condition_txts[temperature_condition]
            progress['speed_condition_txt'] = 'Speed : ' + condition_txts[speed_condition]

            progress['temperature'] = data[3]
            progress['target_speed'] = int.from_bytes(data[4:6],byteorder='little')
            progress['target_spindown_time'] = int.from_bytes(data[6:8],byteorder='little')

            #call callback
            self._calibration_status_callback(progress)

        else:
            # TODO : we could check for unhandled pages, but then we need to know which pages are already handled by base class
            pass

        # base class gets everything too, so it can handle the wait for page events
        super().on_antplus_bcdata(data)

    def get_resistance (self):
        #we could send a request for page 48, but this data arrives continuously on page 17
        return self.status['cur_resistance']

    # resistance = int between 0 & 200
    def set_resistance (self, resistance):
        resistance_value = int(resistance)
        if resistance_value >= 0 and resistance_value <= 200:
            self.status['set_resistance'] = resistance_value #store so we can monitor later
            _reserved = 0xFF
            set_resistance_req = array.array('B',[FECDevice.Page.CONTROL_BASIC_RESISTANCE,
                                                 _reserved,_reserved,_reserved,_reserved,_reserved,_reserved,
                                                 resistance_value])
            self.channel.send_acknowledged_data(set_resistance_req) #sync by channel.py
                
    def get_target_power(self):
        # apparently there is no response on FECDevice.Page.CONTROL_TARGET_POWER
        # only way to know is to send command_status and check if ID = CONTROL_TARGET_POWER
        cur_target_power = None
        cmd_status = self.get_command_status()
        if cmd_status['last_cmd_id'] == FECDevice.Page.CONTROL_TARGET_POWER and cmd_status['cmd_status'] == 0: # 0 = Pass
            cmd_data = cmd_status['cmd_data']
            cur_target_power = int.from_bytes(cmd_data[2:4],byteorder='little')
        return cur_target_power

    # target_power between 0 & 4000W in 0.25W increments
    def set_target_power (self, target_power):
        if target_power >= 0.0 and target_power <= 4000.0:
            self.status['set_target_power'] = target_power #store so we can monitor later
            target_power_value = int(target_power * 4.0) & 0xFFFF
            _reserved = 0xFF
            req_data = array.array('B',[FECDevice.Page.CONTROL_TARGET_POWER,
                                        _reserved,_reserved,_reserved,_reserved,_reserved] + 
                                        list(target_power_value.to_bytes(2,byteorder='little')))
            self.channel.send_acknowledged_data(req_data) #sync by channel.py

    # use the units from the device profile
    def set_wind_resistance (self, wind_speed=0xFF, wind_resistance_coeff=0xFF, drafting_factor=0xFF):
            _reserved = 0xFF
            req_data = array.array('B',[FECDevice.Page.CONTROL_WIND_RESISTANCE,
                                        _reserved,_reserved,_reserved,_reserved,
                                        wind_resistance_coeff,wind_speed,drafting_factor])
            self.channel.send_acknowledged_data(req_data) #sync by channel.py
            _logger.info(f"set_track_resistance, send data : {req_data}")

    # use the units from the device profile
    # grade : -200% -> 200%, rolling_resistance_coeff : 0 -> 0.0127 (0.004 default = asphalt road, 0.001 = wooden track)
    def set_track_resistance (self, grade=None, rolling_resistance_coeff = None):
            _reserved = 0xFF
            if grade:
                grade_value = int((200.0+grade)*100.0) & 0xFFFF
            else:
                grade_value = 0xFFFF # default
            if rolling_resistance_coeff:
                rr_coeff_value = int(rolling_resistance_coeff*20000.0) & 0xFF
            else:
                rr_coeff_value = 0xFF # default

            req_data = array.array('B',[FECDevice.Page.CONTROL_TRACK_RESISTANCE,_reserved,_reserved,_reserved,_reserved]
            + list(grade_value.to_bytes(2,byteorder='little')) + [rr_coeff_value])
            self.channel.send_acknowledged_data(req_data) #sync by channel.py
            _logger.info(f"set_track_resistance, send data : {req_data}")

    def get_capabilities(self):
        self._request_data_page(FECDevice.Page.FE_CAPABILITIES)
        self._wait_for_page_data(FECDevice.Page.FE_CAPABILITIES)
        # the data are now appended to self.info by on_antplus_bcdata
        return self.info

    def get_user_config(self):
        self._request_data_page(FECDevice.Page.USER_CONFIG)
        self._wait_for_page_data(FECDevice.Page.USER_CONFIG)
        # the data are now appended to self.user by on_antplus_bcdata
        return self.user

    # user_weight, bicycle_weight in kg, wheel_diameter in mm, gear_ratio : 0.03 -> 7.65
    # no range checks done here
    # we don't get a FECDevice.Page.USER_CONFIG with the updated values automatically!
    # call to get_user_config() will update self.user
    def set_user_config(self,user_weight=None,bicycle_weight=None, wheel_diam=None, gear_ratio=0.0):
        _reserved = 0xFF
        #defaults to override
        user_weight_value = 0xFFFF #trainer will assume 75.0kg default
        bicycle_weight_value = 0xFFF #trainer will assume 10.0kg default
        wheel_diam_cm = 0xFF # trainer will assume 700mm
        wheel_diam_mm = 0xF
        if user_weight :
            user_weight_value = int(user_weight*100.0) & 0xFFFF
        if bicycle_weight:
            bicycle_weight_value = int(bicycle_weight*20.0) & 0xFFF
        if wheel_diam:
            wheel_diam_cm = int(wheel_diam / 10.0) & 0xFF
            wheel_diam_mm = int(wheel_diam - 10*wheel_diam_cm) & 0xF
        gear_ratio_value = int(gear_ratio / 0.03) & 0xFF

        req_data = array.array('B',[FECDevice.Page.USER_CONFIG] 
                                   + list(user_weight_value.to_bytes(2,byteorder='little')) 
                                   + [_reserved, wheel_diam_mm + ((bicycle_weight_value & 0xF) << 4), 
                                   bicycle_weight_value >> 4,wheel_diam_cm, gear_ratio_value])
        self.channel.send_acknowledged_data(req_data) #sync by channel.py
        _logger.info(f"set_user_config, send data : {req_data}")

    def start_calibration(self, calibration_type=None, status_callback=None):
        # TODO : why doesn't the function definition accept calibration_type=FECDevice.CalibrationType.SPIN_DOWN_CALIBRATION (default param)??
        calibration_type = calibration_type or FECDevice.CalibrationType.SPIN_DOWN_CALIBRATION
        _reserved = 0x0
        _unused = 0xFF
        if status_callback:
            self._calibration_status_callback = status_callback # replace the default callback
        req_data = array.array('B',[FECDevice.Page.CALIBRATION_REQUEST_RESPONSE, calibration_type,
                                    _reserved,_unused,_unused,_unused,_unused,_unused])
        _logger.info(f"start_calibration:sending request data : {req_data}")
        self.channel.send_acknowledged_data(req_data) #sync by channel.py

    def stop_calibration(self):
        _reserved = 0x0
        _unused = 0xFF
        req_data = array.array('B',[FECDevice.Page.CALIBRATION_REQUEST_RESPONSE, FECDevice.CalibrationType.CANCEL,
                                    _reserved,_unused,_unused,_unused,_unused,_unused])
        _logger.info(f"stop_calibration:sending request data : {req_data}")
        self.channel.send_acknowledged_data(req_data) #sync by channel.py

    def _calibration_status_callback (self, status):
        # the default callback for calibration status updates
        _logger.info(f"calibration status : {status}")
