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


import logging

from ant.base.message import Message
from ant.easy.exception import TransferFailedException
from ant.easy.filter import wait_for_event, wait_for_response, wait_for_special

_logger = logging.getLogger("ant.easy.channel")


class Channel:
    class Type:
        BIDIRECTIONAL_RECEIVE = 0x00
        BIDIRECTIONAL_TRANSMIT = 0x10

        SHARED_BIDIRECTIONAL_RECEIVE = 0x20
        SHARED_BIDIRECTIONAL_TRANSMIT = 0x30

        UNIDIRECTIONAL_RECEIVE_ONLY = 0x40
        UNIDIRECTIONAL_TRANSMIT_ONLY = 0x50

    def __init__(self, id, node, ant):
        self.id = id
        self._node = node
        self._ant = ant

    def wait_for_event(self, ok_codes):
        # sds add chNum, so we can match events for a particular channel
        return wait_for_event(
            ok_codes, self.id, self._node._events, self._node._event_cond
        )
        # return wait_for_event(ok_codes, self._node._events, self._node._event_cond)

    def wait_for_response(self, event_id):
        return wait_for_response(
            event_id, self._node._responses, self._node._responses_cond
        )

    def wait_for_special(self, event_id):
        return wait_for_special(
            event_id, self._node._responses, self._node._responses_cond
        )

    def _assign(self, channelType, networkNumber, ext_assign):
        self._ant.assign_channel(self.id, channelType, networkNumber, ext_assign)
        return self.wait_for_response(Message.ID.ASSIGN_CHANNEL)

    def _unassign(self):
        pass

    def open(self):
        self._ant.open_channel(self.id)
        return self.wait_for_response(Message.ID.OPEN_CHANNEL)

    def open_rx_scan_mode(self):
        self._ant.open_rx_scan_mode()
        return self.wait_for_response(Message.ID.OPEN_RX_SCAN_MODE)

    # sds - nog niet helemaal clean want de id blijft wel bezet, maar zo kunnen we al eens testen
    def close(self):
        self._ant.close_channel(self.id)
        return self.wait_for_response(Message.ID.CLOSE_CHANNEL)

    def set_id(self, deviceNum, deviceType, transmissionType):
        self._ant.set_channel_id(self.id, deviceNum, deviceType, transmissionType)
        return self.wait_for_response(Message.ID.SET_CHANNEL_ID)

    def set_period(self, messagePeriod):
        self._ant.set_channel_period(self.id, messagePeriod)
        return self.wait_for_response(Message.ID.SET_CHANNEL_PERIOD)

    def set_search_timeout(self, timeout):
        self._ant.set_channel_search_timeout(self.id, timeout)
        return self.wait_for_response(Message.ID.SET_CHANNEL_SEARCH_TIMEOUT)

    def set_rf_freq(self, rfFreq):
        self._ant.set_channel_rf_freq(self.id, rfFreq)
        return self.wait_for_response(Message.ID.SET_CHANNEL_RF_FREQ)

    def enable_extended_messages(self, enable):
        self._ant.enable_extended_messages(self.id, enable)
        return self.wait_for_response(Message.ID.ENABLE_EXT_RX_MESGS)

    def set_search_waveform(self, waveform):
        self._ant.set_search_waveform(self.id, waveform)
        return self.wait_for_response(Message.ID.SET_SEARCH_WAVEFORM)

    def request_message(self, messageId):
        _logger.debug("requesting message %#02x", messageId)
        self._ant.request_message(self.id, messageId)
        _logger.debug("done requesting message %#02x", messageId)
        return self.wait_for_special(messageId)

    def send_broadcast_data(self, data):
        _logger.debug("send broadcast data %s", self.id)
        self._ant.send_broadcast_data(self.id, data)

    def send_acknowledged_data(self, data):
        # SDS WORKAROUND : eerst kijken of nog uitstaande TX_COMPLETED events in de node._events zitten voor dit channel
        # voor het geval er nog een is aangekomen buiten timeout van een vorige send_acknowledged_data
        # momenteel verhindert niets om meerdere send_acknowledged_data op hetzelfde channel terzelfdertijd te starten vanuit <> threads
        # dus deze workaround kan deze events wel onterecht wissen!
        self._node._event_cond.acquire()
        msgs_to_delete = []
        for message in self._node._events:
            if (message[0], message[1], message[2][0]) == (
                self.id,
                1,
                Message.Code.EVENT_TRANSFER_TX_COMPLETED,
            ):
                msgs_to_delete.append(message)

        for message in msgs_to_delete:
            self._node._events.remove(message)

        self._node._event_cond.release()

        # start of original code:
        try:
            _logger.debug("send acknowledged data %s", self.id)
            self._ant.send_acknowledged_data(self.id, data)
            self.wait_for_event([Message.Code.EVENT_TRANSFER_TX_COMPLETED])
            _logger.debug("done sending acknowledged data %s", self.id)
        except TransferFailedException:
            _logger.warning("failed to send acknowledged data %s, retrying", self.id)
            self.send_acknowledged_data(data)

    def send_burst_transfer_packet(self, channelSeq, data, first):
        _logger.debug("send burst transfer packet %s", data)
        self._ant.send_burst_transfer_packet(channelSeq, data, first)

    def send_burst_transfer(self, data):
        try:
            _logger.debug("send burst transfer %s", self.id)
            self._ant.send_burst_transfer(self.id, data)
            self.wait_for_event([Message.Code.EVENT_TRANSFER_TX_START])
            self.wait_for_event([Message.Code.EVENT_TRANSFER_TX_COMPLETED])
            _logger.debug("done sending burst transfer %s", self.id)
        except TransferFailedException:
            _logger.warning("failed to send burst transfer %s, retrying", self.id)
            self.send_burst_transfer(data)
