# Ant-FS
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

import logging
import os
import sys
import struct
import unittest

from ant.easy.node import Node, Message
from ant.easy.channel import Channel


class AntEasyTests(unittest.TestCase):
    @unittest.skipUnless("ANT_TEST_USB_STICK" in os.environ, "Testing with USB stick not enabled")
    def test_search(self):

        try:
            logger = logging.getLogger("ant")
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(fmt='%(asctime)s  %(name)-15s  %(levelname)-8s  %(message)s'))
            logger.addHandler(handler)

            self.node = Node()
            print("Request basic information...")
            m = self.node.request_message(Message.ID.RESPONSE_ANT_VERSION)
            print("  ANT version:  ", struct.unpack("<10sx", m[2])[0])
            m = self.node.request_message(Message.ID.RESPONSE_CAPABILITIES)
            print("  Capabilities: ", m[2])
            m = self.node.request_message(Message.ID.RESPONSE_SERIAL_NUMBER)
            print("  Serial number:", struct.unpack("<I", m[2])[0])

            print("Starting system...")

            NETWORK_KEY = [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]

            # self.node.reset_system()
            self.node.set_network_key(0x00, NETWORK_KEY)

            c = self.node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

            c.set_period(4096)
            c.set_search_timeout(255)
            c.set_rf_freq(50)
            c.set_search_waveform([0x53, 0x00])
            c.set_id(0, 0x01, 0)

            print("Open channel...")
            c.open()
            c.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)

            print("Searching...")

            self.node.start()

            print("Done")
        except KeyboardInterrupt:
            print("Interrupted")
            self.node.stop()
            sys.exit(1)

    def stop(self):
        self.node.stop()
