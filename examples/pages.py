import logging

from ant.base.message import Message

_logger = logging.getLogger("ant.plus.pages")

class pages:
    def __init__(self, deviceType):
        #  1, "Sync"
        # 11, "Bike Power Sensors"
        # 15, "Multi-Sport Speed and Distance"
        # 16, "Controls"
        # 16, "Ranging"
        # 17, "Fitness Equipment Devices"
        # 18, "Blood Pressure Monitors"
        # 19, "Geocache Transmitters"
        # 20, "Light Electric Vehicle"
        # 25, "Environment Sensors"
        # 26, "Racquet"
        # 30, "Running Dynamics"
        # 31, "Muscle Oxygen"
        # 34, "Shifting"
        # 40, "Bike Radar"
        # 41, "Tracker"
        #115, "Dropper Seatpost"
        #116, "Suspension"
        #119, "Weight Scale"
        #120, "Heart Rate Sensors"
        #121, "Bike Speed and Cadence Sensors"
        #122, "Bike Cadence Sensors"
        #123, "Bike Speed Sensors"
        #124, "Stride-Based Speed and Distance Sensors"
        #-1, "Unknown"
        
        self.deviceType = deviceType
    
    def on_data(self, data):
        data_package = {}
        if self.deviceType == 120:
            data_package["data_page"] = data[0] >> 0 & 7 #Data Page Number
            data_package["heart_beat_event_time"] = data[4]+(data[5]<<8) #Represents the time of the last valid heart beat event. Units: 1/1024 second. Range or Rollover: 63.999
            data_package["heart_beat_count"] = data[6] #A single byte value which increments with each heart beat event. Range or Rollover: 256 counts
            data_package["computed_heart_rate"] = data[7] #Instantaneous heart rate. This value is intended to be displayed by the display device without further interpretation. If Invalid set to 0x00. Range or Rollover 1-255
            
            if data_package["computed_heart_rate"] == Message.ID.INVALID:
                _logger.warning("received computed heart rate invalid")
            
            #Cumulative Operating Time
            if data_package["data_page"] == 0x01:
                #Description: Increments every 2 seconds and is reset on battery replacement
                #Units: 2 seconds
                #Rollover every 33554430s
                data_package["cumulative_operating_time"] = (data[1] + (data[2]<<8)+(data[3]<<16))*2 #in seconds
            
            #Manufacturer Information
            if data_package["data_page"] == 0x02:
                data_package["manufacturer_ID"] = data[1] #Refer to FIT SDK for a current list of all manufacturer IDs.
                data_package["serial_number"] = data[2]+(data[3]<<8) #This is the upper 16 bits of the 4 byte serial number.
            
            #Product Information
            if data_package["data_page"] == 0x03:
                data_package["hardware_version"] = data[1] #To be set by the manufacturer
                data_package["software_version"] = data[2] #To be set by the manufacturer
                data_package["model_number"] = data[3] #To be set by the manufacturer
            
            #Previous Heart Beat
            if data_package["data_page"] == 0x04:
                if data[1] == 0xFF:
                    data_package["manufacturer_specific"] = data[1] #Set to 0xFF if not used. The receiver shall [self-verify] not interpret this data unless custom behaviour is defined for a specific manufacturer.
                else:
                    data_package["manufacturer_specific"] = "not used"
                #Represents the time of the previous valid heart beat event. Units 1/1024 second, roll over 63.999s (~64s)
                data_package["previous_heart_beat_event_time"] = (data[2] + (data[3]<<8))/1024 #in seconds
            
            #Swim Interval Summary
            if data_package["data_page"] == 0x05:
                if data[1] != 0x00:
                    #Average heart rate over the current interval in progress (if active) or the most recently completed interval (if resting). An interval is a segment of the athletic workout.
                    #Valid Value = 1 – 255bpm. This value is intended to be displayed by the display device without further interpretation.
                    data_package["interval_average_heart_rate"] = data[1] #In beats per minute
                else:
                    data_package["interval_average_heart_rate"] = "invalid"
                    _logger.warning("received interval average heart_rate invalid")
                
                if data[2] != 0x00:
                    #Maximum heart rate over the current interval in progress (if active) or the most recently completed interval (if resting). An interval is a segment of the athletic workout.
                    #Valid Value = 1 – 255bpm. This value is intended to be displayed by the display device without further interpretation.
                    data_package["interval_maximum_heart_rate"] = data[2] #In beats per minute
                else:
                    data_package["interval_maximum_heart_rate"] = "invalid"
                    _logger.warning("received interval maximum heart rate invalid")
                
                if data[3] != 0x00:
                    #Average heart rate over the current session in progress. A session spans over the entire activity and may contain multiple intervals.
                    #Valid Value = 1 – 255bpm. This value is intended to be displayed by the display device without further interpretation.
                    data_package["session_average_heart_rate"] = data[3] #In beats per minute
                else:
                    data_package["session_average_heart_rate"] = "invalid"
                    _logger.warning("received session average heart rate invalid")
            
            #Capabilities
            if data_package["data_page"] == 0x06:
                #Byte 1: The transmitter shall [MD_0010] set this value = 0xFF. The receiver shall [SD_0007] not interpret this field at this time.
                #Byte 2, Bits 0-2: Bit field to indicate which features are supported by the heart rate monitor. If the bit is set to 1, the feature is supported.
                #Byte 2, Bits 3-5: Reserved. Set to 0
                #Byte 2, Bits 6-7: Manufacturer-Specific Features
                data_package["extended_running_features_supported"] = bool(data[2] >> 0 & 1)
                data_package["extended_cycling_features_supported"] = bool(data[2] >> 1 & 1)
                data_package["extended_swimming_features_supported"] = bool(data[2] >> 2 & 1)
                #Byte 3, Bits 0-2: Bit field to indicate which features are supported by the heart rate monitor. If the bit is set to 1, the feature is supported.
                #Byte 3, Bits 3-5: Reserved. Set to 0
                #Byte 3, Bits 6-7: Manufacturer-Specific Features
                data_package["extended_running_features_enabled"] = bool(data[3] >> 0 & 1)
                data_package["extended_cycling_features_enabled"] = bool(data[3] >> 1 & 1)
                data_package["extended_swimming_features_enabled"] = bool(data[3] >> 2 & 1)
            
            #Battery Status
            if data_package["data_page"] == 0x07:
                #Battery Level Percentage Reserved Values: 0x65 – 0xFE Set to 0xFF if not used. Units: in %. Range:0-100%
                battery_level = data[1] # in %
                #Value = 0 – 255 (0x00 – 0xFF). Units 1/256 (V)
                fractional_battery_voltage = data[2]/256 # in V
                #Battery Status and Coarse Battery Voltage. See Table 6-12 for more details.
                descriptive_bit_field = data[3]
                coarse_battery_voltage = descriptive_bit_field >> 0 & 4 # in V
                if coarse_battery_voltage != 0x0F:
                    data_package["battery_voltage"] = fractional_battery_voltage + coarse_battery_voltage
                    data_package["battery_level"] = battery_level
                    battery_status = descriptive_bit_field >> 4 & 3 # in bpm
                    if battery_status == 0x01:
                        data_package["battery_status"] = "New"
                    if battery_status == 0x02:
                        data_package["battery_status"] = "Good"
                    if battery_status == 0x03:
                        data_package["battery_status"] = "Ok"
                    if battery_status == 0x04:
                        data_package["battery_status"] = "Low"
                    if battery_status == 0x05:
                        data_package["battery_status"] = "Critical"
                    #0x06 Reserved for future use
                    if battery_status == 0x07:
                        data_package["battery_status"] = "invalid"
                        _logger.warning("received battery status invalid")
                else:
                    data_package["battery_voltage"] = "invalid"
                    _logger.warning("received coarse battery voltage invalid")
                    data_package["battery_level"] = "not used"
                    #Bits 7: Receiver will not interpret this value at this time.
        
        #check for extended message
        if len(data)>8:
            if data[8]==int("0x80",16): #flag byte for extended messages
                deviceNumberLSB = data[9]
                deviceNumberMSB = data[10]
                data_package["device_number"]=deviceNumberLSB + (deviceNumberMSB<<8)
                data_package["device_type"]=data[11]
                #Transmission Type Bit Field
                #Bits 0-1: 
                #   00: Reserved 
                #   01: Independent Channel
                #   10: Shared Channel using 1 byte address (if supported)
                #   11: Shared Channel using 2 byte address
                #Bit 2: Optional for non-ANT+ managed networks:
                #   0: Global data pages not used 
                #   1: Global data pages used (e.g. ANT+ Common Data pages)
                #Bit 3: Undefined – set to zero.
                #Bit 4-7: Optional extension of the device number (MSN)
                data_package["trans_type"]=data[12]
        print(data_package)
        return data_package
