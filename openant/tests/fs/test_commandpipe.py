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
import datetime

from openant.fs.commandpipe import (
    parse,
    CreateFile,
    Request,
    CommandPipe,
    Time,
    TimeResponse,
)


class CreateFileTest(unittest.TestCase):
    def runTest(self):
        # Test create file
        data = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        request = CreateFile(len(data), 0x80, [0x04, 0x00, 0x00], [0x00, 0xFF, 0xFF])

        # Test create file response
        response_data = array.array(
            "B", b"\x02\x00\x00\x00\x04\x00\x00\x00\x80\x04\x7b\x00\x67\x00\x00\x00"
        )
        response = parse(response_data)
        self.assertEqual(response.get_request_id(), 0x04)
        self.assertEqual(response.get_response(), 0x00)
        self.assertEqual(response.get_data_type(), 0x80)  # FIT
        self.assertEqual(response.get_identifier(), array.array("B", b"\x04\x7b\x00"))
        self.assertEqual(response.get_index(), 103)


class TimeTest(unittest.TestCase):
    def runTest(self):
        # Test time request
        request = Request(CommandPipe.Type.TIME)
        self.assertEqual(
            request.get(),
            array.array(
                "B",
                b"\x01\x00\x00"
                + CommandPipe._sequence.to_bytes(1, byteorder="big")
                + b"\x03\x00\x00\x00",
            ),
        )

        # Test time parse
        response_data = array.array(
            "B", b"\x03\x00\x00\x0F\x78\xB5\xCA\x25\xC8\xA0\xF4\x29\x01\x00\x00\x00"
        )
        response = parse(response_data)
        self.assertIsInstance(response, Time)
        self.assertEqual(response.get_command(), 0x03)
        self.assertEqual(response.get_sequence(), 0x0F)
        current_time = (
            datetime.datetime(2010, 2, 2, 10, 42, 0)
            - datetime.datetime(1989, 12, 31, 0, 0, 0)
        ).total_seconds()
        self.assertEqual(response.get_current_time(), current_time)
        system_time = (
            datetime.datetime(2012, 4, 20, 23, 10, 0)
            - datetime.datetime(1989, 12, 31, 0, 0, 0)
        ).total_seconds()
        self.assertEqual(response.get_system_time(), system_time)
        self.assertEqual(response.get_time_format(), 1)

        # Test time create
        current_time = (
            datetime.datetime(2015, 1, 4, 21, 23, 30)
            - datetime.datetime(1989, 12, 31, 0, 0, 0)
        ).total_seconds()
        system_time = (
            datetime.datetime(2012, 4, 20, 23, 10, 0)
            - datetime.datetime(1989, 12, 31, 0, 0, 0)
        ).total_seconds()

        time = Time(int(current_time), int(system_time), Time.Format.COUNTER)
        self.assertEqual(
            time.get(),
            array.array(
                "B",
                b"\x03\x00\x00"
                + CommandPipe._sequence.to_bytes(1, byteorder="big")
                + b"\x52\x63\x0c\x2f\xc8\xa0\xf4\x29\x02\x00\x00\x00",
            ),
        )

        # Test time request response
        response_data = array.array(
            "B", b"\x02\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        response = parse(response_data)
        self.assertIsInstance(response, TimeResponse)
