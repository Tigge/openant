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

from ant.fs.command import parse, DownloadRequest, DownloadResponse, AuthenticateCommand


class AuthenticateCommandTest(unittest.TestCase):
    def test_serial(self):
        command = AuthenticateCommand(
            AuthenticateCommand.Request.SERIAL, 123456789)
        self.assertEqual(command.get(), array.array('B',
                                                    [0x44, 0x04, 0x01, 0x00, 0x15, 0xcd, 0x5b, 0x7]))

    def test_pairing(self):
        command = AuthenticateCommand(
            AuthenticateCommand.Request.PAIRING, 987654321,
            map(ord, 'hello'))
        self.assertEqual(command.get(), array.array('B',
                                                    [0x44, 0x04, 0x02, 0x05, 0xb1, 0x68, 0xde, 0x3a,
                                                     0x68, 0x65, 0x6c, 0x6c, 0x6f, 0x00, 0x00, 0x00]))


class DownloadRequestTest(unittest.TestCase):
    def test(self):
        # Download request
        data = array.array('B', [0x44, 0x09, 0x5f, 0x00, 0x00, 0xba, 0x00,
                                 0x00, 0x00, 0x00, 0x9e, 0xc2, 0x00, 0x00, 0x00, 0x00])

        request = parse(data)
        self.assertIsInstance(request, DownloadRequest)


class DownloadResponseTest(unittest.TestCase):
    def test_ok(self):
        # Download response, ok
        data = array.array('B', [68, 137, 0, 0, 8, 0, 0, 0,
                                 0, 0, 0, 0, 8, 0, 0, 0,
                                 2, 0, 0, 1, 3, 0, 3, 0,
                                 0, 0, 0, 0, 0, 0, 188, 173])

        response = parse(data)
        self.assertIsInstance(response, DownloadResponse)
        self.assertEqual(response._get_argument("response"), DownloadResponse.Response.OK)
        self.assertEqual(response._get_argument("remaining"), 8)
        self.assertEqual(response._get_argument("offset"), 0)
        self.assertEqual(response._get_argument("size"), 8)
        self.assertEqual(response._get_argument("data"), array.array('B', [2, 0, 0, 1, 3, 0, 3, 0]))
        self.assertEqual(response._get_argument("crc"), 44476)

    def test_not_readable(self):

        # Download response, failed
        data = array.array('B', [68, 137, 2, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 119, 239, 36, 174])
        response = parse(data)
        self.assertIsInstance(response, DownloadResponse)
        self.assertEqual(response._get_argument("response"), DownloadResponse.Response.NOT_READABLE)
        self.assertEqual(response._get_argument("remaining"), 0)
        self.assertEqual(response._get_argument("data"), array.array('B', []))
        self.assertEqual(response._get_argument("crc"), 0)

