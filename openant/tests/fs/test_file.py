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
import sys

from openant.fs.file import Directory
from openant.fs.file import File


class DirectoryParse(unittest.TestCase):
    def test_parse(self):

        self.dir = array.array(
            "B",
            b"\x01\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00"
            b"\x01\x0c\x00\x00\x00\x50\x00\xe0\x19\x00\x00\x00\x00\x00\x02\x00\x01\x0d"
            b"\x00\x00\x00\x30\x00\x00\x04\x00\x00\x00\x00\x00\x03\x00\x80\x01\xff\xff"
            b"\x00\x90\x5c\x02\x00\x00\x00\x00\x00\x00\x04\x00\x80\x02\xff\xff\x00\xd0"
            b"\x1d\x02\x00\x00\x00\x00\x00\x00\x05\x00\x80\x03\x03\x00\x00\xd0\xac\x04"
            b"\x00\x00\x00\x00\x00\x00\x06\x00\x80\x03\x01\x00\x00\xd0\xac\x04\x00\x00"
            b"\x00\x00\x00\x00\x07\x00\x80\x04\x21\x00\x00\xb0\x20\x09\x00\x00\x80\xfa"
            b"\xd5\x29\x08\x00\x80\x04\x22\x00\x00\xb0\xa0\x31\x00\x00\x82\xfa\xd5\x29"
            b"\x09\x00\x80\x04\x23\x00\x00\xb0\xb8\x17\x00\x00\x82\xfa\xd5\x29\x0a\x00"
            b"\x80\x04\x24\x00\x00\xb0\xe9\x02\x00\x00\x82\xfa\xd5\x29\x0b\x00\x80\x04"
            b"\x25\x00\x00\xb0\x8b\x03\x00\x00\x84\xfa\xd5\x29\x0c\x00\x80\x04\x26\x00"
            b"\x00\xb0\xe9\x02\x00\x00\x84\xfa\xd5\x29\x0d\x00\x80\x04\x27\x00\x00\xb0"
            b"\x2d\x04\x00\x00\x86\xfa\xd5\x29\x0e\x00\x80\x04\x28\x00\x00\xb0\x31\x1d"
            b"\x00\x00\x86\xfa\xd5\x29\x0f\x00\x80\x04\x29\x00\x00\xb0\x59\x1a\x00\x00"
            b"\x86\xfa\xd5\x29\x10\x00\x80\x04\x2a\x00\x00\xb0\xad\x3d\x00\x00\x88\xfa"
            b"\xd5\x29\x11\x00\x80\x04\x2b\x00\x00\xb0\x50\x43\x00\x00\x8a\xfa\xd5\x29"
            b"\x12\x00\x80\x04\x2c\x00\x00\xb0\x6b\x2e\x00\x00\x8a\xfa\xd5\x29\x13\x00"
            b"\x80\x04\x2d\x00\x00\xb0\x28\x1a\x00\x00\x8c\xfa\xd5\x29\x14\x00\x80\x04"
            b"\x2e\x00\x00\xb0\xd9\x17\x00\x00\x8c\xfa\xd5\x29\x15\x00\x80\x04\x2f\x00"
            b"\x00\xb0\x6c\x03\x00\x00\x90\xfa\xd5\x29\x16\x00\x80\x04\x30\x00\x00\xb0"
            b"\xa6\x50\x00\x00\x90\xfa\xd5\x29\x17\x00\x80\x04\x31\x00\x00\xb0\x9f\x3e"
            b"\x00\x00\x92\xfa\xd5\x29\x18\x00\x80\x04\x32\x00\x00\xb0\xfd\x0f\x00\x00"
            b"\x94\xfa\xd5\x29\x19\x00\x80\x04\x33\x00\x00\xb0\xa3\x18\x00\x00\x96\xfa"
            b"\xd5\x29\x1a\x00\x80\x04\x34\x00\x00\xb0\x38\x19\x00\x00\x96\xfa\xd5\x29"
            b"\x1b\x00\x80\x04\x35\x00\x00\xb0\x9e\x16\x00\x00\x98\xfa\xd5\x29\x1c\x00"
            b"\x80\x04\x36\x00\x00\xb0\x72\x13\x00\x00\x9a\xfa\xd5\x29\x1d\x00\x80\x04"
            b"\x37\x00\x00\xb0\xef\x17\x00\x00\x9a\xfa\xd5\x29\x1e\x00\x80\x04\x38\x00"
            b"\x00\xb0\x9b\x23\x00\x00\x9c\xfa\xd5\x29\x1f\x00\x80\x04\x39\x00\x00\xb0"
            b"\x9c\x13\x00\x00\x9e\xfa\xd5\x29",
        )

        directory = Directory.parse(self.dir)
        self.assertEqual(directory.get_version(), (0, 1))
        self.assertEqual(directory.get_time_format(), 0)
        self.assertEqual(directory.get_current_system_time(), 0)
        self.assertEqual(directory.get_last_modified(), 0)
        self.assertEqual(len(directory.get_files()), 31)


class FileParse(unittest.TestCase):
    def test_parse(self):
        self.file_binary = array.array(
            "B", b"\x07\x00\x80\x04\x21\x00\x00\xb0\x20\x09\x00\x00\x80\xfa\xd5\x29"
        )

        file_object = File.parse(self.file_binary)
        self.assertEqual(file_object.get_index(), 7)
        self.assertEqual(file_object.get_type(), File.Type.FIT)
        self.assertEqual(
            file_object.get_identifier(), array.array("B", b"\x04\x21\x00")
        )
        self.assertEqual(file_object.get_fit_sub_type(), File.Identifier.ACTIVITY)
        self.assertEqual(file_object.get_fit_file_number(), 33)
        self.assertEqual(file_object.get_size(), 2336)
        self.assertEqual(
            file_object.get_date().year, datetime.datetime(2012, 3, 28, 17, 12, 32).year
        )
        if sys.version_info >= (3, 3):
            self.assertEqual(
                file_object.get_date(),
                datetime.datetime(
                    2012, 3, 28, 17, 12, 32, tzinfo=datetime.timezone.utc
                ),
            )
        self.assertTrue(file_object.is_readable())
        self.assertFalse(file_object.is_writable())
        self.assertTrue(file_object.is_erasable())
        self.assertTrue(file_object.is_archived())
        self.assertFalse(file_object.is_append_only())
        self.assertFalse(file_object.is_encrypted())
        self.assertEqual(file_object.get_flags_string(), "r-eA--")
