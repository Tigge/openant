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

import array
import unittest
import datetime

from ant.fs.commandpipe import parse, CreateFile, Request, CommandPipe, Time, TimeResponse


class CreateFileTest(unittest.TestCase):
    def runTest(self):
        # Test create file
        data = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09]
        request = CreateFile(len(data), 0x80, [0x04, 0x00, 0x00], [0x00, 0xff, 0xff])

        # Test create file response
        response_data = array.array('B', [2, 0, 0, 0, 4, 0, 0, 0, 128, 4, 123, 0, 103, 0, 0, 0])
        response = parse(response_data)
        self.assertEqual(response.get_request_id(), 0x04)
        self.assertEqual(response.get_response(), 0x00)
        self.assertEqual(response.get_data_type(), 0x80)  # FIT
        self.assertEqual(response.get_identifier(), array.array('B', [4, 123, 0]))
        self.assertEqual(response.get_index(), 103)


class TimeTest(unittest.TestCase):
    def runTest(self):
        # Test time request
        request = Request(CommandPipe.Type.TIME)
        self.assertEqual(request.get(), array.array('B', [0x01, 0x00, 0x00, CommandPipe._sequence, 0x03, 0x00, 0x00, 0x00]))

        # Test time parse
        response_data = array.array('B', [0x03, 0x00, 0x00, 0x0f, 0x78, 0xb5, 0xca, 0x25,
                                          0xc8, 0xa0, 0xf4, 0x29, 0x01, 0x00, 0x00, 0x00])
        response = parse(response_data)
        self.assertIsInstance(response, Time)
        self.assertEqual(response.get_command(), 0x03)
        self.assertEqual(response.get_sequence(), 0x0f)
        current_time = (datetime.datetime(2010, 2, 2, 10, 42, 0) - datetime.datetime(1989, 12, 31, 0, 0, 0)).total_seconds()
        self.assertEqual(response.get_current_time(), current_time)
        system_time = (datetime.datetime(2012, 4, 20, 23, 10, 0) - datetime.datetime(1989, 12, 31, 0, 0, 0)).total_seconds()
        self.assertEqual(response.get_system_time(), system_time)
        self.assertEqual(response.get_time_format(), 1)

        # Test time create
        current_time = (datetime.datetime(2015, 1, 4, 21, 23, 30) - datetime.datetime(1989, 12, 31, 0, 0, 0)).total_seconds()
        system_time = (datetime.datetime(2012, 4, 20, 23, 10, 0) - datetime.datetime(1989, 12, 31, 0, 0, 0)).total_seconds()

        time = Time(int(current_time), int(system_time), Time.Format.COUNTER)
        self.assertEqual(time.get(), array.array('B', [0x03, 0x00, 0x00, CommandPipe._sequence, 0x52, 0x63, 0x0c, 0x2f,
                                                       0xc8, 0xa0, 0xf4, 0x29, 0x02, 0x00, 0x00, 0x00]))

        # Test time request response
        response_data = array.array('B', [0x02, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00,
                                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        response = parse(response_data)
        self.assertIsInstance(response, TimeResponse)

