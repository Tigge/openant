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
import sys

from ant.fs.file import Directory
from ant.fs.file import File


class DirectoryParse(unittest.TestCase):

    def test_parse(self):
        self.dir = array.array('B', [1, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                     0, 0, 0, 1, 0, 1, 12, 0, 0, 0, 80, 0, 224, 25, 0, 0, 0, 0, 0, 2,
                                     0, 1, 13, 0, 0, 0, 48, 0, 0, 4, 0, 0, 0, 0, 0, 3, 0, 128, 1, 255,
                                     255, 0, 144, 92, 2, 0, 0, 0, 0, 0, 0, 4, 0, 128, 2, 255, 255,
                                     0, 208, 29, 2, 0, 0, 0, 0, 0, 0, 5, 0, 128, 3, 3, 0, 0, 208,
                                     172, 4, 0, 0, 0, 0, 0, 0, 6, 0, 128, 3, 1, 0, 0, 208, 172, 4,
                                     0, 0, 0, 0, 0, 0, 7, 0, 128, 4, 33, 0, 0, 176, 32, 9, 0, 0, 128,
                                     250, 213, 41, 8, 0, 128, 4, 34, 0, 0, 176, 160, 49, 0, 0, 130,
                                     250, 213, 41, 9, 0, 128, 4, 35, 0, 0, 176, 184, 23, 0, 0, 130,
                                     250, 213, 41, 10, 0, 128, 4, 36, 0, 0, 176, 233, 2, 0, 0, 130,
                                     250, 213, 41, 11, 0, 128, 4, 37, 0, 0, 176, 139, 3, 0, 0, 132,
                                     250, 213, 41, 12, 0, 128, 4, 38, 0, 0, 176, 233, 2, 0, 0, 132,
                                     250, 213, 41, 13, 0, 128, 4, 39, 0, 0, 176, 45, 4, 0, 0, 134, 250,
                                     213, 41, 14, 0, 128, 4, 40, 0, 0, 176, 49, 29, 0, 0, 134, 250, 213,
                                     41, 15, 0, 128, 4, 41, 0, 0, 176, 89, 26, 0, 0, 134, 250, 213, 41,
                                     16, 0, 128, 4, 42, 0, 0, 176, 173, 61, 0, 0, 136, 250, 213, 41, 17,
                                     0, 128, 4, 43, 0, 0, 176, 80, 67, 0, 0, 138, 250, 213, 41, 18, 0,
                                     128, 4, 44, 0, 0, 176, 107, 46, 0, 0, 138, 250, 213, 41, 19, 0,
                                     128, 4, 45, 0, 0, 176, 40, 26, 0, 0, 140, 250, 213, 41, 20, 0, 128,
                                     4, 46, 0, 0, 176, 217, 23, 0, 0, 140, 250, 213, 41, 21, 0, 128, 4,
                                     47, 0, 0, 176, 108, 3, 0, 0, 144, 250, 213, 41, 22, 0, 128, 4, 48,
                                     0, 0, 176, 166, 80, 0, 0, 144, 250, 213, 41, 23, 0, 128, 4, 49, 0,
                                     0, 176, 159, 62, 0, 0, 146, 250, 213, 41, 24, 0, 128, 4, 50, 0, 0,
                                     176, 253, 15, 0, 0, 148, 250, 213, 41, 25, 0, 128, 4, 51, 0, 0,
                                     176, 163, 24, 0, 0, 150, 250, 213, 41, 26, 0, 128, 4, 52, 0, 0,
                                     176, 56, 25, 0, 0, 150, 250, 213, 41, 27, 0, 128, 4, 53, 0, 0,
                                     176, 158, 22, 0, 0, 152, 250, 213, 41, 28, 0, 128, 4, 54, 0, 0,
                                     176, 114, 19, 0, 0, 154, 250, 213, 41, 29, 0, 128, 4, 55, 0, 0,
                                     176, 239, 23, 0, 0, 154, 250, 213, 41, 30, 0, 128, 4, 56, 0, 0,
                                     176, 155, 35, 0, 0, 156, 250, 213, 41, 31, 0, 128, 4, 57, 0, 0,
                                     176, 156, 19, 0, 0, 158, 250, 213, 41])

        directory = Directory.parse(self.dir)
        self.assertEqual(directory.get_version(), (0, 1))
        self.assertEqual(directory.get_time_format(), 0)
        self.assertEqual(directory.get_current_system_time(), 0)
        self.assertEqual(directory.get_last_modified(), 0)
        self.assertEqual(len(directory.get_files()), 31)


class FileParse(unittest.TestCase):

    def test_parse(self):
        self.file_binary = array.array('B', [7, 0, 128, 4, 33, 0, 0, 176, 32, 9, 0, 0, 128, 250, 213, 41])

        file_object = File.parse(self.file_binary)
        self.assertEqual(file_object.get_index(), 7)
        self.assertEqual(file_object.get_type(), File.Type.FIT)
        self.assertEqual(file_object.get_identifier(), array.array('B', [4, 33, 0]))
        self.assertEqual(file_object.get_fit_sub_type(),File.Identifier.ACTIVITY)
        self.assertEqual(file_object.get_fit_file_number(), 33)
        self.assertEqual(file_object.get_size(), 2336)
        self.assertEqual(file_object.get_date().year, datetime.datetime(2012, 3, 28, 17, 12, 32).year)
        if sys.version_info >= (3,3):
            self.assertEqual(file_object.get_date(), datetime.datetime(2012, 3, 28, 17, 12, 32, tzinfo=datetime.timezone.utc))
        self.assertTrue(file_object.is_readable())
        self.assertFalse(file_object.is_writable())
        self.assertTrue(file_object.is_erasable())
        self.assertTrue(file_object.is_archived())
        self.assertFalse(file_object.is_append_only())
        self.assertFalse(file_object.is_encrypted())
        self.assertEqual(file_object.get_flags_string(), "r-eA--")
