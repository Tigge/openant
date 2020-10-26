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


from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.base.message import Message

import logging
import struct
import threading
import sys

NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]


def on_data(data):
    heartrate = data[7]
    string = "Heartrate: " + str(heartrate) + " [BPM]"

    sys.stdout.write(string)
    sys.stdout.flush()
    sys.stdout.write("\b" * len(string))
    if len(data) > 8:
        print(data)
        deviceNumberLSB = data[9]
        deviceNumberMSB = data[10]
        deviceNumber = "{}".format(deviceNumberLSB + (deviceNumberMSB << 8))
        deviceType = "{}".format(data[11])
        print("New Device Found: %s of type %s" % (deviceNumber, deviceType))


def main():
    logging.basicConfig(filename="example.log", level=logging.DEBUG)

    node = Node()
    node.set_network_key(0x00, NETWORK_KEY)

    channel = node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE, 0x00, 0x01)

    channel.on_broadcast_data = on_data
    channel.on_burst_data = on_data
    channel.on_acknowledge = on_data

    channel.set_id(0, 120, 0)
    channel.enable_extended_messages(1)
    channel.set_search_timeout(0xFF)
    channel.set_period(8070)
    channel.set_rf_freq(57)

    try:
        channel.open()
        node.start()
    finally:
        node.stop()


if __name__ == "__main__":
    main()
