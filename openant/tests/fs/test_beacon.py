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


import array
import unittest

from openant.fs.beacon import Beacon


class BeaconParseTest(unittest.TestCase):
    def test_beacon_parse(self):
        data = array.array("B", b"\x43\x04\x00\x03\x41\x05\x01\x00")

        beacon = Beacon.parse(data)
        self.assertIsInstance(beacon, Beacon)
        self.assertFalse(beacon.is_data_available())
        self.assertFalse(beacon.is_upload_enabled())
        self.assertFalse(beacon.is_pairing_enabled())
        self.assertEqual(beacon.get_channel_period(), 4)
        self.assertEqual(
            beacon.get_client_device_state(), Beacon.ClientDeviceState.LINK
        )
        self.assertEqual(beacon.get_serial(), 66881)
        self.assertEqual(beacon.get_descriptor(), (1345, 1))
