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

from openant.fs.command import (
    parse,
    DownloadRequest,
    DownloadResponse,
    AuthenticateCommand,
)


class AuthenticateCommandTest(unittest.TestCase):
    def test_serial(self):
        command = AuthenticateCommand(AuthenticateCommand.Request.SERIAL, 123456789)
        self.assertEqual(
            command.get(),
            array.array("B", b"\x44\x04\x01\x00\x15\xCD\x5B\x07"),
        )

    def test_pairing(self):
        command = AuthenticateCommand(
            AuthenticateCommand.Request.PAIRING, 987654321, map(ord, "hello")
        )
        self.assertEqual(
            command.get(),
            array.array(
                "B", b"\x44\x04\x02\x05\xB1\x68\xDE\x3A\x68\x65\x6C\x6C\x6F\x00\x00\x00"
            ),
        )


class DownloadRequestTest(unittest.TestCase):
    def test(self):
        # Download request
        data = array.array(
            "B", b"\x44\x09\x5F\x00\x00\xBA\x00\x00\x00\x00\x9E\xC2\x00\x00\x00\x00"
        )

        request = parse(data)
        self.assertIsInstance(request, DownloadRequest)


class DownloadResponseTest(unittest.TestCase):
    def test_ok(self):
        # Download response, ok
        data = array.array(
            "B",
            b"\x44\x89\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x02"
            b"\x00\x00\x01\x03\x00\x03\x00\x00\x00\x00\x00\x00\x00\xBC\xAD",
        )

        response = parse(data)
        self.assertIsInstance(response, DownloadResponse)
        self.assertEqual(
            response._get_argument("response"), DownloadResponse.Response.OK
        )
        self.assertEqual(response._get_argument("remaining"), 8)
        self.assertEqual(response._get_argument("offset"), 0)
        self.assertEqual(response._get_argument("size"), 8)
        self.assertEqual(
            response._get_argument("data"),
            array.array("B", b"\x02\x00\x00\x01\x03\x00\x03\x00"),
        )
        self.assertEqual(response._get_argument("crc"), 44476)

    def test_not_readable(self):
        # Download response, failed
        data = array.array(
            "B", b"\x44\x89\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x77\xef\x24\xae"
        )
        response = parse(data)
        self.assertIsInstance(response, DownloadResponse)
        self.assertEqual(
            response._get_argument("response"), DownloadResponse.Response.NOT_READABLE
        )
        self.assertEqual(response._get_argument("remaining"), 0)
        self.assertEqual(response._get_argument("data"), array.array("B", []))
        self.assertEqual(response._get_argument("crc"), 0)
