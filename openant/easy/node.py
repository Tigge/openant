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


import collections
import threading
import logging
import queue
from typing import Optional, List

from ..base.ant import Ant
from ..base.message import Message
from ..easy.channel import Channel
from ..easy.filter import wait_for_event, wait_for_response, wait_for_special

_logger = logging.getLogger("openant.easy.node")


class Node:
    def __init__(self):

        self._responses_cond = threading.Condition()
        self._responses = collections.deque()
        self._event_cond = threading.Condition()
        self._events = collections.deque()

        self._datas = queue.Queue()

        # will replace with response from node at open
        self.serial: Optional[int] = None
        self.ant_version: Optional[str] = None
        self.max_networks = 8
        self.max_channels = 8
        self.channels = {}

        self.ant = Ant()

        self._running = True

        self._worker_thread = threading.Thread(target=self._worker, name="openant.easy")
        self._worker_thread.start()

    def new_channel(
        self, ctype: int, network_number: int = 0x00, ext_assign: Optional[int] = None
    ):
        num = len(self.channels)
        if num >= self.max_channels:
            raise RuntimeError(
                f"Cannot create new channel #{num}: >= supported number of channels {self.max_channels}"
            )
        elif network_number >= self.max_networks:
            raise RuntimeError(
                f"Cannot create new channel #{num}: network {network_number} out of range"
            )
        channel = Channel(num, self, self.ant)
        self.channels[num] = channel
        channel._assign(ctype, network_number, ext_assign)
        return channel

    def request_message(self, messageId: int):
        _logger.debug("requesting message %#02x", messageId)
        self.ant.request_message(0, messageId)
        _logger.debug("done requesting message %#02x", messageId)
        return self.wait_for_special(messageId)

    def get_capabilities(self):
        """Sends request for capabilities but will not wait so that it can be sent before main loop"""
        self.ant.request_message(0, Message.ID.RESPONSE_CAPABILITIES)

    def get_meta_data(self):
        """Sends request for node meta data but will not wait so that it can be sent before main loop"""
        self.ant.request_message(0, Message.ID.RESPONSE_SERIAL_NUMBER)
        self.ant.request_message(0, Message.ID.RESPONSE_ANT_VERSION)

    def set_network_key(self, network: int, key: List[int]):
        if network >= self.max_networks:
            raise RuntimeError(f"Network {network} out of range")
        self.ant.set_network_key(network, key)
        return self.wait_for_response(Message.ID.SET_NETWORK_KEY)

    def set_led(self, enabled):
        self.ant.set_led(enabled)
        return self.wait_for_special(Message.ID.ENABLE_LED)

    def wait_for_event(self, ok_codes):
        return wait_for_event(ok_codes, self._events, self._event_cond)

    def wait_for_response(self, event_id):
        return wait_for_response(event_id, self._responses, self._responses_cond)

    def wait_for_special(self, event_id):
        return wait_for_special(event_id, self._responses, self._responses_cond)

    def _worker_response(self, channel, event, data):
        _logger.debug(f"_worker_response {channel}, {event}, {data}")
        if event == Message.ID.RESPONSE_CAPABILITIES:
            self.max_channels = data[0]
            self.max_networks = data[1]
            _logger.debug(
                f"capabilities max_channels: {self.max_channels}, max_networks {self.max_networks}"
            )
        elif event == Message.ID.RESPONSE_SERIAL_NUMBER:
            self.serial = int.from_bytes(data, byteorder="little")
            _logger.debug(f"serial {self.serial}")
        elif event == Message.ID.RESPONSE_ANT_VERSION:
            self.ant_version = bytes(data).decode("ascii")
            _logger.debug(f"ant_version {self.ant_version}")
        else:
            self._responses_cond.acquire()
            self._responses.append((channel, event, data))
            self._responses_cond.notify()
            self._responses_cond.release()

    def _worker_event(self, channel, event, data):
        _logger.debug(f"_worker_event {channel}, {event}, {data}")
        if event == Message.Code.EVENT_RX_BURST_PACKET:
            self._datas.put(("burst", channel, data))
        elif event == Message.Code.EVENT_RX_BROADCAST:
            self._datas.put(("broadcast", channel, data))
        elif event == Message.Code.EVENT_TX:
            self._datas.put(("broadcast_tx", channel, data))
        elif event == Message.Code.EVENT_RX_ACKNOWLEDGED:
            self._datas.put(("acknowledge", channel, data))
        else:
            self._event_cond.acquire()
            self._events.append((channel, event, data))
            self._event_cond.notify()
            self._event_cond.release()

    def _worker(self):
        self.ant.response_function = self._worker_response
        self.ant.channel_event_function = self._worker_event

        # fire off requests but don't wait until start
        self.get_capabilities()
        self.get_meta_data()
        self.ant.start()

    def _main(self):
        while self._running:
            try:
                (data_type, channel, data) = self._datas.get(True, 1.0)
                self._datas.task_done()

                if data_type == "broadcast":
                    self.channels[channel].on_broadcast_data(data)
                elif data_type == "burst":
                    self.channels[channel].on_burst_data(data)
                elif data_type == "broadcast_tx":
                    self.channels[channel].on_broadcast_tx_data(data)
                elif data_type == "acknowledge":
                    self.channels[channel].on_acknowledge_data(data)
                else:
                    _logger.warning("Unknown data type '%s': %r", data_type, data)
            except queue.Empty as _:
                pass

    def start(self):
        self._main()

    def stop(self):
        if self._running:
            _logger.debug("Stoping openant.easy")
            self._running = False
            self.ant.stop()
            self._worker_thread.join()
