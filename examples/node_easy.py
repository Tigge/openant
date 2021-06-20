import collections
import threading
import logging
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

import pages

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
        channel._deviceType = 120
        channel.enable_extended_messages(1)
        channel.set_search_timeout(0xFF) #Timeout Never
        channel.set_period(messagePeriod)
        channel.set_rf_freq(57)

        if callback is None:
            channel.on_broadcast_data = pages.pages(120).on_data
            channel.on_burst_data = pages.pages(120).on_data
        else:
            channel.on_broadcast_data = callback
            channel.on_burst_data = callback

        channel.open()
    
    def remove_deviceNum(self, deviceNum):
        for i in range(len(self.channels)):
            try:
                if self.channels[i]._deviceNum == deviceNum:
                    self.channels[i].close()
                    time.sleep(0.5)
                    self.channels[i]._unassign()
                    time.sleep(0.5)
                    self.channels[i] = None
            except:
                pass
    
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
            devices_found =[]
            deviceType_on_data = pages.pages(deviceType).on_data
            def scan_data(data):
                data_package = deviceType_on_data(data)
                if "device_number" in data_package.keys():
                    devices_found.append(data_package["device_number"])
            channel.on_broadcast_data = scan_data
            channel.on_burst_data = scan_data
            channel.on_acknowledge = scan_data
            time.sleep(timeout)
            self.remove_channel(channel.id)
            devices_found = list(set(devices_found))
            devices_found.sort()
            if callback is None:
                return devices_found
            else:
                callback(devices_found)
        if callback is None:
            return(tmp_scan())
        else:
            t = threading.Thread(name='scan_ant_daemon', target=tmp_scan)
            t.start()
    
    def stop(self):
        for i in range(len(self.channels)):
            try:
                if self.channels[i] is not None:
                    self.channels[i].close()
                    time.sleep(0.5)
                    self.channels[i]._unassign()
                    self.channels[i] = None
            except:
                pass
        super().stop()

def main():
    n = node_easy()
    NETWORK_KEY= [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]
    n.set_network_key(0x00, NETWORK_KEY)
    
    n.start()
    print("1")
    print(n.scan(120,timeout = 5))
    print("2")
    n.scan(120, timeout = 5, callback=print)
    print("3")
    time.sleep(10)
    print("4")
    n.add_new_hrm(25170)
    time.sleep(10)
    n.scan(120, timeout = 5, callback=print)
    time.sleep(10)
    n.add_new_hrm(49024)
    time.sleep(10)
    n.scan(120, timeout = 5, callback=print)
    time.sleep(10)
    n.remove_deviceNum(25170)
    time.sleep(10)
    n.scan(120, timeout = 5, callback=print)
    time.sleep(10)
    n.remove_deviceNum(49024)
    n.stop()

if __name__ == "__main__":
    main()
