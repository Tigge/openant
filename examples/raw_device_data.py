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
"""
Example shows how to use `on_data` callback to capture and act on raw data from a device - an ANT+ heart rate monitor in this example.

If actually developing a ANT+ device, it's probably better to use the AntPlusDevice parent class in openant.devices.common; refer to how the HeartRate device has been inplemnented.
"""


from openant.easy.node import Node
from openant.easy.channel import Channel

NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]


def on_data(data):
    page = data[0]
    if (page & 0x0F) <= 7:
        heartrate = data[7]
        print(f"heart rate: {heartrate} BPM")

    print(f"on_data: {data}")


def main():
    # uncomment to show verbose module logging
    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    # create the network node with key
    node = Node()
    node.set_network_key(0x00, NETWORK_KEY)

    # create channel
    channel = node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

    # setup callbacks
    channel.on_broadcast_data = on_data
    channel.on_burst_data = on_data

    # setup slave channel
    channel.set_period(8070)
    channel.set_search_timeout(12)
    channel.set_rf_freq(57)
    channel.set_id(0, 120, 0)

    try:
        channel.open()
        node.start()
    finally:
        node.stop()


if __name__ == "__main__":
    main()
