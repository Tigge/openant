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
from collections import OrderedDict
import logging
import struct

from ant.fs.command import Command

_logger = logging.getLogger("ant.fs.commandpipe")


class CommandPipe(object):
    class Type:

        REQUEST = 0x01
        RESPONSE = 0x02
        TIME = 0x03
        CREATE_FILE = 0x04
        DIRECTORY_FILTER = 0x05
        SET_AUTHENTICATION_PASSKEY = 0x06
        SET_CLIENT_FRIENDLY_NAME = 0x07
        FACTORY_RESET_COMMAND = 0x08

    _format = "<BxxB"
    _id = None
    _sequence = 0

    def __init__(self):
        self._arguments = OrderedDict()
        self._add_argument('command', self._id)
        CommandPipe._sequence += 1
        self._add_argument('sequence', CommandPipe._sequence)

    def _add_argument(self, name, value):
        self._arguments[name] = value

    def _get_argument(self, name):
        return self._arguments[name]

    def _get_arguments(self):
        return self._arguments.values()

    def __getattr__(self, attr):
        # Get arguments with get_*
        if attr.startswith("get_"):
            name = attr[4:]
            if name in self._arguments:
                return lambda: self._arguments[name]
        raise AttributeError("No such attribute")

    def get(self):
        arguments = list(self._get_arguments())
        data = struct.pack(self._format, *arguments)
        lst = array.array('B', data)
        _logger.debug("packing %r in %r,%s", data, lst, type(lst))
        return lst

    @classmethod
    def _parse_args(cls, data):
        return struct.unpack(cls._format, data)

    @classmethod
    def _parse(cls, data):
        args = cls._parse_args(data)
        assert args[0] == cls._id
        instance = cls(*args[2:])
        instance._arguments["sequence"] = args[1]
        return instance

    def _debug(self):
        max_key_length, max_value_length = 0, 0
        for key, value in self._arguments.items():
            max_key_length = max(len(str(key)), max_key_length)
            max_value_length = max(len(str(value)), max_value_length)
        max_length = max_key_length + max_value_length + 3
        print("=" * max_length)
        print(self.__class__.__name__)
        print("-" * max_length)
        for key, value in self._arguments.items():
            print(str(key) + ":", " " * (max_length - len(key)), str(value))
        print("=" * max_length)


class Request(CommandPipe):
    _id = CommandPipe.Type.REQUEST
    _format = CommandPipe._format + "Bxxx"

    def __init__(self, request_id):
        CommandPipe.__init__(self)
        self._add_argument('request_id', request_id)


class Response(CommandPipe):
    class Response:
        OK = 0
        FAILED = 1
        REJECTED = 2
        NOT_SUPPORTED = 3

    _id = CommandPipe.Type.RESPONSE
    _format = CommandPipe._format + "BxBx"

    def __init__(self, request_id, response):
        CommandPipe.__init__(self)
        self._add_argument('request_id', request_id)
        self._add_argument('response', response)


class Time(CommandPipe):
    class Format:
        DIRECTORY = 0
        SYSTEM = 1
        COUNTER = 2

    _id = CommandPipe.Type.TIME
    _format = CommandPipe._format + "IIBxxx"

    def __init__(self, current_time, system_time, time_format):
        CommandPipe.__init__(self)
        self._add_argument('current_time', current_time)
        self._add_argument('system_time', system_time)
        self._add_argument('time_format', time_format)


class TimeResponse(Response):
    _format = Response._format + "xxxxxxxx"

    def __init__(self, request_id, response):
        Response.__init__(self, request_id, response)


class CreateFile(Request):
    _id = CommandPipe.Type.CREATE_FILE
    _format = None

    def __init__(self, size, data_type, identifier, identifier_mask):
        CommandPipe.__init__(self)
        self._add_argument('size', size)
        self._add_argument('data_type', data_type)
        self._add_argument('identifier', identifier)
        self._add_argument('identifier_mask', identifier_mask)

    def get(self):
        arguments = list(self._get_arguments())
        data = array.array('B', struct.pack(CommandPipe._format + "IB", *arguments[:4]))
        data.extend(self._get_argument("identifier"))
        data.extend([0])
        data.extend(self._get_argument("identifier_mask"))
        return data

    @classmethod
    def _parse_args(cls, data):
        return struct.unpack(Command._format + "IB", data[0:9]) + (data[9:12],) + (data[13:16],)


class CreateFileResponse(Response):
    _format = Response._format + "BBBBHxx"

    def __init__(self, request_id, response, data_type, identifier, index):
        Response.__init__(self, request_id, response)
        self._add_argument('data_type', data_type)
        self._add_argument('identifier', identifier)
        self._add_argument('index', index)

    @classmethod
    def _parse_args(cls, data):
        return Response._parse_args(data[:8]) + (data[8], data[9:12], struct.unpack("<H", data[12:14])[0])


_classes = {
    CommandPipe.Type.REQUEST: Request,
    CommandPipe.Type.RESPONSE: Response,
    CommandPipe.Type.TIME: Time,
    CommandPipe.Type.CREATE_FILE: CreateFile,
    CommandPipe.Type.DIRECTORY_FILTER: None,
    CommandPipe.Type.SET_AUTHENTICATION_PASSKEY: None,
    CommandPipe.Type.SET_CLIENT_FRIENDLY_NAME: None,
    CommandPipe.Type.FACTORY_RESET_COMMAND: None}

_responses = {
    CommandPipe.Type.TIME: TimeResponse,
    CommandPipe.Type.CREATE_FILE: CreateFileResponse}


def parse(data):
    commandpipe_type = _classes[data[0]]
    if commandpipe_type == Response:
        if data[4] in _responses and len(data) > 8:
            commandpipe_type = _responses[data[4]]
    return commandpipe_type._parse(data)

