#from ant.base import Message
from .. node import Node, Message
from .. channel import Channel

import logging
import os
import struct
import unittest

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
            print "Request basic information..."
            m = self.node.request_message(Message.ID.RESPONSE_VERSION)
            print "  ANT version:  ", struct.unpack("<10sx", m[2])[0]
            m = self.node.request_message(Message.ID.RESPONSE_CAPABILITIES)
            print "  Capabilities: ", m[2]
            m = self.node.request_message(Message.ID.RESPONSE_SERIAL_NUMBER)
            print "  Serial number:", struct.unpack("<I", m[2])[0]

            print "Starting system..."

            NETWORK_KEY= [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]

            #self.node.reset_system()
            self.node.set_network_key(0x00, NETWORK_KEY)

            c = n.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

            c.set_period(4096)
            c.set_search_timeout(255)
            c.set_rf_freq(50)
            c.set_search_waveform([0x53, 0x00])
            c.set_id(0, 0x01, 0)
            
            print "Open channel..."
            c.open()
            c.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)

            print "Searching..."

            self.node.start()

            print "Done"
        except KeyboardInterrupt:
            print "Interrupted"
            self.node.stop()
            sys.exit(1)

    def stop():
        self.node.stop()
