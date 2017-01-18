# Ant
#
# Copyright (c) 2017, Rhys Kidd <rhyskidd@gmail.com>
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

import array
import unittest

from ant.base.message import Message


class MessageParse(unittest.TestCase):

    def test_message_parse(self):
        data = array.array('B', [0xa4, 0x03, 0x40, 0x00, 0x46, 0x00, 0xa1])
        message = Message.parse(data)
        self.assertIsInstance(message, Message)

    # Add known != 0xa4 assert
    #def test_bad_sync_message_parse(self):
    #    data = array.array('B', [0x00, 0x03, 0x40, 0x00, 0x46, 0x00, 0xa1])
    #    self.assertIsInstance(Message.parse(data), None)

    # Add known invalid checksum assert    

    def test_message_code_lookup(self):
        self.assertEqual(Message.Code.lookup(Message.Code.EVENT_RX_SEARCH_TIMEOUT), "EVENT_RX_SEARCH_TIMEOUT")
        self.assertEqual(Message.Code.lookup(1), "EVENT_RX_SEARCH_TIMEOUT")

    def test_message_code_lookup_fail(self):
        self.assertEqual(Message.Code.lookup(4444), None)
