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
import datetime
import logging
import threading
import queue

from ant.easy.channel import Channel
from ant.easy.node import Node, Message

import ant.fs.command
from ant.fs.beacon import Beacon
from ant.fs.command import (
    LinkCommand,
    DownloadRequest,
    DownloadResponse,
    AuthenticateCommand,
    AuthenticateResponse,
    DisconnectCommand,
    UploadRequest,
    UploadResponse,
    UploadDataCommand,
    UploadDataResponse,
    EraseRequestCommand,
    EraseResponse,
)
from ant.fs.commandpipe import CreateFile, Response, Time, TimeResponse
from ant.fs.file import Directory
from ant.fs.commons import crc

_logger = logging.getLogger("ant.fs.manager")


class AntFSException(Exception):
    def __init__(self, error, errno=None):
        Exception.__init__(self, error, errno)
        self._error = error
        self._errno = errno

    def get_error(self):
        if self._errno is not None:
            return str(self._errno) + ": " + self._error
        else:
            return self._error


class AntFSDownloadException(AntFSException):
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)


class AntFSUploadException(AntFSException):
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)


class AntFSEraseException(AntFSException):
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)


class AntFSAuthenticationException(AntFSException):
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)


class AntFSCreateFileException(AntFSException):
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)


class AntFSTimeException(AntFSException):
    def __init__(self, error, errno=None):
        AntFSException.__init__(self, error, errno)


class Application:
    _serial_number = 1337
    _frequency = 19  # 0 to 124, x - 2400 (in MHz)

    def __init__(self):

        self._queue = queue.Queue()
        self._beacons = queue.Queue()

        self._node = Node()

        try:
            NETWORK_KEY = [0xA8, 0xA4, 0x23, 0xB9, 0xF5, 0x5E, 0x63, 0xC1]
            self._node.set_network_key(0x00, NETWORK_KEY)

            print("Request basic information...")

            m = self._node.request_message(Message.ID.RESPONSE_CAPABILITIES)
            print("  Capabilities: ", m[2])

            # m = self._node.request_message(Message.ID.RESPONSE_ANT_VERSION)
            # print "  ANT version:  ", struct.unpack("<10sx", m[2])[0]

            # m = self._node.request_message(Message.ID.RESPONSE_SERIAL_NUMBER)
            # print "  Serial number:", struct.unpack("<I", m[2])[0]

            print("Starting system...")

            # NETWORK_KEY= [0xa8, 0xa4, 0x23, 0xb9, 0xf5, 0x5e, 0x63, 0xc1]
            # self._node.set_network_key(0x00, NETWORK_KEY)

            print("Key done...")

            self._channel = self._node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
            self._channel.on_broadcast_data = self._on_data
            self._channel.on_burst_data = self._on_data

            self.setup_channel(self._channel)

            self._worker_thread = threading.Thread(target=self._worker, name="ant.fs")
            self._worker_thread.start()
        except Exception as e:
            self.stop()
            raise e

    def _worker(self):
        self._node.start()

    def _main(self):
        try:
            _logger.debug("Link level")
            beacon = self._get_beacon()
            if self.on_link(beacon):
                for i in range(0, 5):
                    beacon = self._get_beacon()
                    if (
                        beacon.get_client_device_state()
                        == Beacon.ClientDeviceState.AUTHENTICATION
                    ):
                        _logger.debug("Auth layer")
                        if self.on_authentication(beacon):
                            _logger.debug("Authenticated")
                            beacon = self._get_beacon()
                            self.on_transport(beacon)
                        self.disconnect()
                        break
        finally:
            _logger.debug("Run 5")
            self.stop()

    def _on_beacon(self, data):
        b = Beacon.parse(data)
        self._beacons.put(b)

    def _on_command(self, data):
        c = ant.fs.command.parse(data)
        self._queue.put(c)

    def _on_data(self, data):
        # print "_on_data", data, len(data)
        if data[0] == 0x43:
            self._on_beacon(data[:8])
            if len(data[8:]) > 0:
                self._on_command(data[8:])
        elif data[0] == 0x44:
            self._on_command(data)

    def _get_beacon(self):
        b = self._beacons.get()
        self._beacons.task_done()
        return b

    def _get_command(self, timeout=15.0):
        _logger.debug("Get command, t%d, s%d", timeout, self._queue.qsize())
        c = self._queue.get(True, timeout)
        self._queue.task_done()
        return c

    def _send_command(self, c):
        data = c.get()
        if len(data) == 8:
            self._channel.send_acknowledged_data(data)
        else:
            self._channel.send_burst_transfer(data)

    # Application actions are defined from here
    # =======================================================================

    # These should be overloaded:

    def setup_channel(self, channel):
        pass

    def on_link(self, beacon):
        pass

    def on_authentication(self, beacon):
        pass

    def on_transport(self, beacon):
        pass

    # Shouldn't have to touch these:

    def start(self):
        self._main()

    def stop(self):
        self._node.stop()

    def _send_commandpipe(self, data):
        # print "send commandpipe", data
        self.upload(0xFFFE, data)

    def _get_commandpipe(self):
        # print "get commandpipe"
        return ant.fs.commandpipe.parse(self.download(0xFFFE))

    def create(self, typ, data, callback=None):
        # print "create", typ
        request = CreateFile(len(data), 0x80, [typ, 0x00, 0x00], [0x00, 0xFF, 0xFF])
        self._send_commandpipe(request.get())
        result = self._get_commandpipe()
        # result._debug()

        if result.get_response() != Response.Response.OK:
            raise AntFSCreateFileException(
                "Could not create file", result.get_response()
            )

        # print "create result", result, result.get_index(), result.get_data_type(), result.get_identifier()
        # d = self.download_directory()

        # Inform the application that the upload request was successfully created
        if callback is not None:
            callback(0)

        self.upload(result.get_index(), data, callback)
        return result.get_index()

    def upload(self, index, data, callback=None):
        # print "upload", index, len(data)

        iteration = 0
        while True:

            # Request Upload

            # Continue using Last Data Offset (special MAX_ULONG value)
            request_offset = 0 if iteration == 0 else 0xFFFFFFFF
            self._send_command(UploadRequest(index, len(data), request_offset))

            upload_response = self._get_command()
            # upload_response._debug()

            if upload_response._get_argument("response") != UploadResponse.Response.OK:
                raise AntFSUploadException(
                    "Upload request failed", upload_response._get_argument("response")
                )

            # Upload data
            offset = upload_response._get_argument("last_data_offset")
            max_block = upload_response._get_argument("maximum_block_size")
            # print " uploading", offset, "to", offset + max_block
            data_packet = data[offset : offset + max_block]
            crc_seed = upload_response._get_argument("crc")
            crc_val = crc(data_packet, upload_response._get_argument("crc"))

            # Pad with 0 to even 8 bytes
            missing_bytes = 8 - (len(data_packet) % 8)
            if missing_bytes != 8:
                data_packet.extend(array.array("B", [0] * missing_bytes))
                # print " adding", str(missing_bytes), "padding"

            # print " packet", len(data_packet)
            # print " crc   ", crc_val, "from seed", crc_seed

            self._send_command(
                UploadDataCommand(crc_seed, offset, data_packet, crc_val)
            )
            upload_data_response = self._get_command()
            # upload_data_response._debug()
            if (
                upload_data_response._get_argument("response")
                != UploadDataResponse.Response.OK
            ):
                raise AntFSUploadException(
                    "Upload data failed", upload_data_response._get_argument("response")
                )

            if callback is not None and len(data) != 0:
                callback((offset + len(data_packet)) / len(data))

            if offset + len(data_packet) >= len(data):
                # print " done"
                break

            # print " one more"
            iteration += 1

    def download(self, index, callback=None):
        offset = 0
        initial = True
        crc = 0
        data = array.array("B")
        while True:
            _logger.debug("Download %d, o%d, c%d", index, offset, crc)
            self._send_command(DownloadRequest(index, offset, True, crc))
            _logger.debug("Wait for response...")
            try:
                response = self._get_command()
                if response._get_argument("response") == DownloadResponse.Response.OK:
                    remaining = response._get_argument("remaining")
                    offset = response._get_argument("offset")
                    total = offset + remaining
                    data[offset:total] = response._get_argument("data")[:remaining]
                    # print "rem", remaining, "offset", offset, "total", total, "size", response._get_argument("size")
                    # TODO: check CRC

                    if callback is not None and response._get_argument("size") != 0:
                        callback(total / response._get_argument("size"))
                    if total == response._get_argument("size"):
                        return data
                    crc = response._get_argument("crc")
                    offset = total
                else:
                    raise AntFSDownloadException(
                        "Download request failed: ", response._get_argument("response")
                    )
            except queue.Empty:
                _logger.debug("Download %d timeout", index)
                # print "recover from download failure"

    def download_directory(self, callback=None):
        data = self.download(0, callback)
        return Directory.parse(data)

    def set_time(self, time=datetime.datetime.utcnow()):
        """
        :param time: datetime in UTC, or None to set to current time
        """
        utc_tai_diff_seconds = 35
        offset = time - datetime.datetime(1989, 12, 31, 0, 0, 0)
        t = Time(int(offset.total_seconds()) + utc_tai_diff_seconds, 0xFFFFFFFF, 0)
        self._send_commandpipe(t.get())

        result = self._get_commandpipe()

        if result.get_response() != TimeResponse.Response.OK:
            raise AntFSTimeException("Failed to set time", result.get_response())

    def erase(self, index):
        self._send_command(EraseRequestCommand(index))
        response = self._get_command()

        if (
            response._get_argument("response")
            != EraseResponse.Response.ERASE_SUCCESSFUL
        ):
            raise AntFSDownloadException(
                "Erase request failed: ", response._get_argument("response")
            )

    def link(self):
        self._channel.request_message(Message.ID.RESPONSE_CHANNEL_ID)
        self._send_command(LinkCommand(self._frequency, 4, self._serial_number))

        # New period, search timeout
        self._channel.set_period(4096)
        self._channel.set_search_timeout(10)
        self._channel.set_rf_freq(self._frequency)

    def authentication_serial(self):
        self._send_command(
            AuthenticateCommand(AuthenticateCommand.Request.SERIAL, self._serial_number)
        )
        response = self._get_command()
        return (response.get_serial(), response.get_data_string())

    def authentication_passkey(self, passkey):
        self._send_command(
            AuthenticateCommand(
                AuthenticateCommand.Request.PASSKEY_EXCHANGE,
                self._serial_number,
                passkey,
            )
        )

        response = self._get_command()
        if response._get_argument("type") == AuthenticateResponse.Response.ACCEPT:
            return response.get_data_array()
        else:
            raise AntFSAuthenticationException(
                "Passkey authentication failed", response._get_argument("type")
            )

    def authentication_pair(self, friendly_name):
        data = array.array("B", map(ord, list(friendly_name)))
        self._send_command(
            AuthenticateCommand(
                AuthenticateCommand.Request.PAIRING, self._serial_number, data
            )
        )

        response = self._get_command(30)
        if response._get_argument("type") == AuthenticateResponse.Response.ACCEPT:
            return response.get_data_array()
        else:
            raise AntFSAuthenticationException(
                "Pair authentication failed", response._get_argument("type")
            )

    def disconnect(self):
        d = DisconnectCommand(DisconnectCommand.Type.RETURN_LINK, 0, 0)
        self._send_command(d)
