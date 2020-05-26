# ANT - Heart Rate Monitor Example
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

from __future__ import absolute_import, print_function

from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.base.message import Message

import logging
import struct
import threading
import sys
import datetime
import time

NETWORK_KEY= [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]


def on_data(data):
    heartrate = data[7]
    string = "Heartrate: " + str(heartrate) + " [BPM]"

    sys.stdout.write(string)
    sys.stdout.flush()
    sys.stdout.write("\b" * len(string))
    if len(data)>8:
        print(data)
        deviceNumberLSB = data[9]
        deviceNumberMSB = data[10]
        deviceNumber = "{}".format(deviceNumberLSB + (deviceNumberMSB<<8))
        deviceType = "{}".format(data[11])
        print('New Device Found: %s of type %s' % (deviceNumber,deviceType))


def scan_data(data):
    heartrate = data[7]
    result = {"hbm":heartrate, "rec_time":datetime.datetime.now()}
    if len(data)>8:
        if data[8]==int("0x80",16):
            deviceNumberLSB = data[9]
            deviceNumberMSB = data[10]
            result["device_number"]="{}".format(deviceNumberLSB + (deviceNumberMSB<<8))
            result["device_type"]="{}".format(data[11])
    print(result)
    return result

def hrm_data(data):
    heartrate = data[7]
    result = {"type":"hrm", "hbm":heartrate, "rec_time":datetime.datetime.now()}
    if len(data)>8:
        if data[8]==int("0x80",16):
            deviceNumberLSB = data[9]
            deviceNumberMSB = data[10]
            result["device_number"]="{}".format(deviceNumberLSB + (deviceNumberMSB<<8))
            result["device_type"]="{}".format(data[11])
    print(result)
    return result

def main():
    logging.basicConfig(filename='example.log',level=logging.DEBUG)

    node = Node()
    node.set_network_key(0x00, NETWORK_KEY)

    channel_scan = node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE,0x00,0x01)

    channel_scan.on_broadcast_data = scan_data
    channel_scan.on_burst_data = scan_data
    channel_scan.on_acknowledge = scan_data

    channel_scan.set_id(0, 120, 0)
    channel_scan.enable_extended_messages(1)
    channel_scan.set_search_timeout(0xFF)
    channel_scan.set_period(8070)
    channel_scan.set_rf_freq(57)


    channel_hrm = node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

    channel_hrm.on_broadcast_data = hrm_data
    channel_hrm.on_burst_data = hrm_data
    channel_hrm.on_acknowledge = hrm_data

    channel_hrm.set_id(49024, 120, 0)
    channel_hrm.enable_extended_messages(1)
    channel_hrm.set_search_timeout(0xFF)
    channel_hrm.set_period(32280)
    channel_hrm.set_rf_freq(57)

    channel_hrm2 = node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

    channel_hrm2.on_broadcast_data = hrm_data
    channel_hrm2.on_burst_data = hrm_data
    channel_hrm2.on_acknowledge = hrm_data

    channel_hrm2.set_id(25170, 120, 0)
    channel_hrm2.enable_extended_messages(1)
    channel_hrm2.set_search_timeout(0xFF)
    channel_hrm2.set_period(32280)
    channel_hrm2.set_rf_freq(57)
    try:
        channel_scan.open()
        time.sleep(10)
        channel_scan.close()
        channel_scan._unassign()
        channel_hrm.open()
        channel_hrm2.open()
        #channel_scan.open()
        node.start()
    finally:
        channel_hrm.close()
        channel_hrm._unassign()
        channel_hrm2.close()
        channel_hrm2._unassign()
        node.stop()

if __name__ == "__main__":
    main()
