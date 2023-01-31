"""
Base ANT interfacing
"""
# Ant
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
import collections
import struct
import threading
import time
import queue
import logging

import usb.core
import usb.util
from usb import USBError

from .message import Message
from .commons import format_list
from .driver import find_driver

_logger = logging.getLogger("openant.base.ant")


class Ant:
    """Provides ANT data interface and manages data from a `Driver` via a worker thread"""

    _RESET_WAIT = 1

    def __init__(self):

        self._driver = find_driver()

        self._message_queue_cond = threading.Condition()
        self._message_queue = collections.deque()

        self._events = queue.Queue()

        self._buffer = array.array("B", [])
        self._burst_data = array.array("B", [])
        self._last_data = array.array("B", [])

        self._running = True

        self._driver.open()

        self._worker_thread = threading.Thread(target=self._worker, name="openant.base")
        self._worker_thread.start()

        self.reset_system()

    def start(self):
        self._main()

    def stop(self):
        if self._running:
            _logger.debug("Stoping openant.base")
            self._running = False
            self._worker_thread.join()
            self._driver.close()

    def _on_broadcast(self, message):
        self._events.put(
            (
                "event",
                (message._data[0], Message.Code.EVENT_RX_BROADCAST, message._data[1:]),
            )
        )

    def _on_acknowledge(self, message):
        self._events.put(
            (
                "event",
                (
                    message._data[0],
                    Message.Code.EVENT_RX_ACKNOWLEDGED,
                    message._data[1:],
                ),
            )
        )

    def _on_burst_data(self, message):

        sequence = message._data[0] >> 5
        channel = message._data[0] & 0b00011111
        data = message._data[1:]

        # First sequence
        if sequence == 0:
            self._burst_data = data
        # Other
        else:
            self._burst_data.extend(data)

        # Last sequence (indicated by bit 3)
        if sequence & 0b100 != 0:
            self._events.put(
                (
                    "event",
                    (channel, Message.Code.EVENT_RX_BURST_PACKET, self._burst_data),
                )
            )

    def _worker(self):

        _logger.debug("Ant runner started")

        while self._running:
            try:
                message = self.read_message()

                if message is None:
                    break

                # TODO: flag and extended for broadcast, acknowledge, and burst

                # Only do callbacks for new data. Resent data only indicates
                # a new channel timeslot.
                if not (
                    message._id == Message.ID.BROADCAST_DATA
                    and message._data == self._last_data
                ):

                    # Notifications
                    if message._id in [
                        Message.ID.STARTUP_MESSAGE,
                        Message.ID.SERIAL_ERROR_MESSAGE,
                    ]:
                        _logger.debug("Got response start-up, %r", message)
                        self._events.put(
                            ("response", (None, message._id, message._data))
                        )
                    # Response (no channel)
                    elif message._id in [
                        Message.ID.RESPONSE_ANT_VERSION,
                        Message.ID.RESPONSE_CAPABILITIES,
                        Message.ID.RESPONSE_SERIAL_NUMBER,
                        Message.ID.ENABLE_EXT_RX_MESGS,
                        Message.ID.UNASSIGN_CHANNEL,
                        Message.ID.CLOSE_CHANNEL,
                    ]:
                        _logger.debug("Got response general, %r", message)
                        self._events.put(
                            ("response", (None, message._id, message._data))
                        )
                    # Response (channel)
                    elif message._id in [
                        Message.ID.RESPONSE_CHANNEL_STATUS,
                        Message.ID.RESPONSE_CHANNEL_ID,
                    ]:
                        _logger.debug("Got response channel, %r", message)
                        self._events.put(
                            (
                                "response",
                                (message._data[0], message._id, message._data[1:]),
                            )
                        )
                    # Response (other); Message ID (data[1]) != 0x01)
                    elif (
                        message._id == Message.ID.RESPONSE_CHANNEL
                        and message._data[1] != 0x01
                    ):
                        _logger.debug("Got channel response other, %r", message)
                        self._events.put(
                            (
                                "response",
                                (message._data[0], message._data[1], message._data[2:]),
                            )
                        )
                    # Channel event (Message ID (data[1]) == 0x01 for prefix EVENT_)
                    elif (
                        message._id == Message.ID.RESPONSE_CHANNEL
                        and message._data[1] == 0x01
                    ):
                        _logger.debug("Got channel event, %r", message)
                        self._events.put(
                            (
                                "event",
                                # pass the message code at 2 not message id for event code and it is 0x01
                                (message._data[0], message._data[2], message._data[2:]),
                            )
                        )
                    elif message._id == Message.ID.BROADCAST_DATA:
                        self._on_broadcast(message)
                    elif message._id == Message.ID.ACKNOWLEDGED_DATA:
                        self._on_acknowledge(message)
                    elif message._id == Message.ID.BURST_TRANSFER_DATA:
                        self._on_burst_data(message)
                    else:
                        _logger.warning("Got unknown message, %r", message)
                else:
                    _logger.debug("No new data this period")

                # Send messages in queue, on indicated time slot
                if message._id == Message.ID.BROADCAST_DATA:
                    _logger.debug(
                        "Got broadcast data, examine queue to see if we should send anything back"
                    )
                    if self._message_queue_cond.acquire(blocking=False):
                        while len(self._message_queue) > 0:
                            m = self._message_queue.popleft()
                            self.write_message(m)
                            _logger.debug(" - sent message from queue, %r", m)

                            if (
                                m._id != Message.ID.BURST_TRANSFER_DATA
                                or m._data[0] & 0b10000000
                            ):  # or m._data[0] == 0:
                                break
                        else:
                            _logger.debug(" - no messages in queue")
                        self._message_queue_cond.release()

                self._last_data = message._data

            except USBError as e:
                if not isinstance(e, usb.core.USBTimeoutError):
                    _logger.warning("%s, %r", type(e), e.args)
                else:
                    _logger.debug(f"Timeout waiting for message: {e.args}")

        _logger.debug("Ant runner stopped")

    def _main(self):
        while self._running:
            try:
                (event_type, event) = self._events.get(True, 1.0)
                self._events.task_done()
                (channel, event, data) = event

                if event_type == "response":
                    self.response_function(channel, event, data)
                elif event_type == "event":
                    self.channel_event_function(channel, event, data)
                else:
                    _logger.warning("Unknown message typ '%s': %r", event_type, event)
            except queue.Empty as _:
                pass

    def write_message_timeslot(self, message: Message):
        with self._message_queue_cond:
            self._message_queue.append(message)

    def write_message(self, message: Message):
        data = message.get()
        self._driver.write(data)
        _logger.debug("Write data: %s", format_list(data))

    def read_message(self):
        while self._running:
            # If we have a message in buffer already, return it
            if len(self._buffer) >= 5 and len(self._buffer) >= self._buffer[1] + 4:
                packet = self._buffer[: self._buffer[1] + 4]
                self._buffer = self._buffer[self._buffer[1] + 4 :]
                return Message.parse(packet)
            # Otherwise, read some data and call the function again
            else:
                data = self._driver.read()
                self._buffer.extend(data)
                _logger.debug(
                    "Read data: %s (now have %s in buffer)",
                    format_list(data),
                    format_list(self._buffer),
                )

    def unassign_channel(self, channel):
        message = Message(Message.ID.UNASSIGN_CHANNEL, [channel])
        self.write_message(message)

    def assign_channel(self, channel, channelType, networkNumber, ext_assign):
        if ext_assign is None:
            message = Message(
                Message.ID.ASSIGN_CHANNEL, [channel, channelType, networkNumber]
            )
        else:
            message = Message(
                Message.ID.ASSIGN_CHANNEL,
                [channel, channelType, networkNumber, ext_assign],
            )
        self.write_message(message)

    def open_channel(self, channel):
        message = Message(Message.ID.OPEN_CHANNEL, [channel])
        self.write_message(message)

    def open_rx_scan_mode(self, channel=0):
        """
        Enable RX scanning mode

        In scanning mode, the radio is active in receive mode 100% of the time
        so no other channels but the scanning channel can run. The scanning
        channel picks up any message regardless of period that is being
        transmitted on its RF frequency and matches its channel ID mask. It can
        receive from multiple devices simultaneously.

        A CLOSE_ALL_CHANNELS message from ANT will indicate an invalid attempt
        to start the scanning mode while any channels are open.

        :param channel int: channel number to use (doesn't really matter)
        """
        message = Message(Message.ID.OPEN_RX_SCAN_MODE, [channel, 1])  # [Channel, 1-Enable]
        self.write_message(message)

    def close_channel(self, channel):
        _logger.debug("Closing channel %d", channel)
        message = Message(Message.ID.CLOSE_CHANNEL, [channel])
        self.write_message(message)

    def set_channel_id(self, channel, deviceNum, deviceType, transmissionType):
        data = array.array(
            "B", struct.pack("<BHBB", channel, deviceNum, deviceType, transmissionType)
        )
        message = Message(Message.ID.SET_CHANNEL_ID, data)
        self.write_message(message)

    def set_channel_period(self, channel, messagePeriod):
        data = array.array("B", struct.pack("<BH", channel, messagePeriod))
        message = Message(Message.ID.SET_CHANNEL_PERIOD, data)
        self.write_message(message)

    def set_channel_search_timeout(self, channel, timeout):
        message = Message(Message.ID.SET_CHANNEL_SEARCH_TIMEOUT, [channel, timeout])
        self.write_message(message)

    def set_channel_rf_freq(self, channel, rfFreq):
        message = Message(Message.ID.SET_CHANNEL_RF_FREQ, [channel, rfFreq])
        self.write_message(message)

    def enable_extended_messages(self, channel, enable):
        message = Message(Message.ID.ENABLE_EXT_RX_MESGS, [channel, enable])
        self.write_message(message)

    def set_network_key(self, network, key):
        message = Message(Message.ID.SET_NETWORK_KEY, [network] + key)
        self.write_message(message)

    # This function is a bit of a mystery. It is mentioned in libgant,
    # http://sportwatcher.googlecode.com/svn/trunk/libgant/gant.h and is
    # also sent from the official ant deamon on windows.
    def set_search_waveform(self, channel, waveform):
        message = Message(Message.ID.SET_SEARCH_WAVEFORM, [channel] + waveform)
        self.write_message(message)

    def set_led(self, enabled):
        message = Message(Message.ID.ENABLE_LED, [0x00, enabled])
        self.write_message(message)

    def reset_system(self):
        message = Message(Message.ID.RESET_SYSTEM, [0x00])
        self.write_message(message)
        time.sleep(self._RESET_WAIT)

    def request_message(self, channel, messageId):
        message = Message(Message.ID.REQUEST_MESSAGE, [channel, messageId])
        self.write_message(message)

    def send_broadcast_data(self, channel, data):
        assert len(data) == 8
        message = Message(Message.ID.BROADCAST_DATA, array.array("B", [channel] + data))
        self.write_message(message)

    def send_acknowledged_data(self, channel, data):
        assert len(data) == 8
        message = Message(
            Message.ID.ACKNOWLEDGED_DATA, array.array("B", [channel] + data)
        )
        self.write_message_timeslot(message)

    def send_burst_transfer_packet(self, channel_seq, data, first):
        assert len(data) == 8
        message = Message(
            Message.ID.BURST_TRANSFER_DATA, array.array("B", [channel_seq] + data)
        )
        self.write_message_timeslot(message)

    def send_burst_transfer(self, channel, data):
        assert len(data) % 8 == 0
        _logger.debug("Send burst transfer, chan %s, data %s", channel, data)
        packets = len(data) // 8
        for i in range(packets):
            sequence = ((i - 1) % 3) + 1
            if i == 0:
                sequence = 0
            elif i == packets - 1:
                sequence = sequence | 0b100
            channel_seq = channel | sequence << 5
            packet_data = data[i * 8 : i * 8 + 8]
            _logger.debug(
                "Send burst transfer, packet %d, seq %d, data %s",
                i,
                sequence,
                packet_data,
            )
            self.send_burst_transfer_packet(channel_seq, packet_data, first=i == 0)

    def response_function(self, channel, event, data):
        """Overload to act on generic responses"""
        pass

    def channel_event_function(self, channel, event, data):
        """Overload to act on channel events"""
        pass
