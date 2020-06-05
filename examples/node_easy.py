from __future__ import absolute_import, print_function

import collections
import threading
import logging
import datetime
import time

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue

from ant.base.ant import Ant
from ant.base.message import Message
from ant.easy.channel import Channel
from ant.easy.filter import wait_for_event, wait_for_response, wait_for_special
from ant.easy.node import Node

_logger = logging.getLogger("ant.easy.node")

class node_easy(Node):
    def add_new_hrm(self, deviceNum=0, messagePeriod=32280, callback=None):
        #8070 for 4 messages/second (~4.06 Hz)
        #16140 for 2 messages/second (~2.03 Hz)
        #32280 for 1 message/second (~1.02 Hz)
        channel = self.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
        channel.set_id(deviceNum, 120, 0)
        if deviceNum != 0:
            channel._deviceNum = deviceNum
        channel.enable_extended_messages(1)
        channel.set_search_timeout(0xFF) #Timeout Never
        channel.set_period(messagePeriod)
        channel.set_rf_freq(57)
        def hrm_data(data):
            heartrate = data[7]
            data_package = {"data_page":data[0] >> 0 & 7,
                            "heart_beat_event_time":data[4]+(data[5]<<8),# 1/1024 second
                            "heart_beat_count":data[6], #256 counts
                            "computed_heart_rate":data[7], # 1-255
                            "time_stamp":datetime.datetime.now()}
            if data_package["data_page"] == 1:
                # Increments every 2 seconds and is reset on battery replacement, Rollover every 33554430s
                data_package["cumulative_operating_time"] = (data[1] + (data[2]<<8)+(data[3]<<16))*2 #in seconds
            if data_package["data_page"] == 2:
                data_package["manufacturer_ID"] = data[1]
                data_package["serial_number"] = data[2]+(data[3]<<8)
            if data_package["data_page"] == 3:
                data_package["hardware_version"] = data[1]
                data_package["software_version"] = data[2]
                data_package["model_number"] = data[3]
            if data_package["data_page"] == 4:
                manufacturer_specific = data[1]
                if manufacturer_specific != 255:
                    data_package["manufacturer_specific"] = manufacturer_specific
                else:
                    data_package["manufacturer_specific"] = "not used"
                #Represents the time of the previous valid heart beat event., units 1/1024 second, roll over 63.999s (~64s)
                data_package["previous_heart_beat_event_time"] = (data[2] + (data[3]<<8))/1024 #in seconds
            if data_package["data_page"] == 5:
                interval_average_heart_rate = data[1] # in bpm
                if interval_average_heart_rate != 0:
                    data_package["interval_average_heart_rate"] = interval_average_heart_rate
                else:
                    data_package["interval_average_heart_rate"] = "invalid"
                
                interval_maximum_heart_rate = data[2] # in bpm
                if interval_maximum_heart_rate != 0:
                    data_package["interval_maximum_heart_rate"] = interval_maximum_heart_rate
                else:
                    data_package["interval_maximum_heart_rate"] = "invalid"
                
                session_average_heart_rate = data[3] # in bpm
                if session_average_heart_rate != 0:
                    data_package["session_average_heart_rate"] = session_average_heart_rate
                else:
                    data_package["session_average_heart_rate"] = "invalid"
            if data_package["data_page"] == 6:
                data_package["extended_running_features_supported"] = bool(data[2] >> 0 & 1)
                data_package["extended_cycling_features_supported"] = bool(data[2] >> 1 & 1)
                data_package["extended_swimming_features_supported"] = bool(data[2] >> 2 & 1)
                data_package["extended_running_features_enabled"] = bool(data[3] >> 0 & 1)
                data_package["extended_cycling_features_enabled"] = bool(data[3] >> 1 & 1)
                data_package["extended_swimming_features_enabled"] = bool(data[3] >> 2 & 1)
            if data_package["data_page"] == 7:
                battery_level = data[1] # in %
                fractional_battery_voltage = data[2]/256 # in V
                coarse_battery_voltage = data[3] >> 0 & 4 # in V
                if coarse_battery_voltage != 15:
                    data_package["battery_voltage"] = fractional_battery_voltage + coarse_battery_voltage
                    data_package["battery_level"] = battery_level
                    battery_status = data[3] >> 4 & 3 # in bpm
                    if battery_status == 1:
                        data_package["battery_status"] = "New"
                    if battery_status == 2:
                        data_package["battery_status"] = "Good"
                    if battery_status == 3:
                        data_package["battery_status"] = "Ok"
                    if battery_status == 4:
                        data_package["battery_status"] = "Low"
                    if battery_status == 5:
                        data_package["battery_status"] = "Critical"
                    if battery_status == 7:
                        data_package["battery_status"] = "invalid"
                else:
                    data_package["battery_voltage"] = "invalid"
                    data_package["battery_level"] = "not used"
            if len(data)>8:
                if data[8]==int("0x80",16): #flag byte for extended messages
                    deviceNumberLSB = data[9]
                    deviceNumberMSB = data[10]
                    data_package["device_number"]=deviceNumberLSB + (deviceNumberMSB<<8)
                    data_package["device_type"]=data[11]
            if callback is None:
                print(data_package)
            else:
                try:
                    callback(data_package)
                except:
                    pass
        channel.on_broadcast_data = hrm_data
        channel.open()
    def remove_deviceNum(self, deviceNum):
        for i in range(len(self.channels)):
            try:
                if self.channels[i]._deviceNum == deviceNum:
                    self.channels[i].close()
                    self.channels[i]._unassign()
                    self.channels[i] = None
            except:
                pass
    def start(self):
        self._main_thread = threading.Thread(target=self._main, name="_main")
        self._main_thread.start()
    def stop(self):
        if self._running:
            _logger.debug("Stoping ant.easy")
            self._running = False
            self.ant.stop()
            self._worker_thread.join()
            self._main_thread.join()
    def scan(self, deviceType, timeout = 5, callback=None):
        def tmp_scan():
            #8070 for 4 messages/second (~4.06 Hz)
            #16140 for 2 messages/second (~2.03 Hz)
            #32280 for 1 message/second (~1.02 Hz)
            channel = self.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE,0x00,0x01)
            channel.set_id(0, deviceType, 0)
            channel.enable_extended_messages(1)
            channel.set_search_timeout(0xFF)
            channel.set_period(8070)
            channel.set_rf_freq(57)
            channel.open()
            channel._devices_found =[]
            def scan_data(data):
                data_package = {}
                if len(data)>8:
                    if data[8]==int("0x80",16): #flag byte for extended messages
                        deviceNumberLSB = data[9]
                        deviceNumberMSB = data[10]
                        data_package["device_number"]=deviceNumberLSB + (deviceNumberMSB<<8)
                        data_package["device_type"]=data[11]
                        channel._devices_found.append(data_package)
            channel.on_broadcast_data = scan_data
            channel.on_burst_data = scan_data
            channel.on_acknowledge = scan_data
            time.sleep(timeout)
            if callback is None:
                print(channel._devices_found)
            else:
                callback(channel._devices_found)
            self.remove_channel(channel.id)
        t = threading.Thread(name='scan_daemon', target=tmp_scan)
        t.start()

def main():
    n = node_easy()
    NETWORK_KEY= [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]
    n.set_network_key(0x00, NETWORK_KEY)
    def print_hrm(data):
        print(data)
    n.start()
    n.scan(120)
    n.add_new_hrm(25170,callback=print_hrm)
    time.sleep(10)
    n.remove_deviceNum(25170)
    n.channels[0]._deviceNum
    n.channels[0].on_broadcast_data=print

if __name__ == "__main__":
    main()
