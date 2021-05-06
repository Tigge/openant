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

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue

from ant.base.ant import Ant
from ant.base.message import Message
from ant.easy.channel import Channel
from ant.easy.filter import wait_for_event, wait_for_response, wait_for_special

_logger = logging.getLogger("ant.easy.node")


class Node:
    def __init__(self):

        self._responses_cond = threading.Condition()
        self._responses = collections.deque()
        self._event_cond = threading.Condition()
        self._events = collections.deque()
        self._main_thread = None

        self._datas = queue.Queue()

        self.ant = Ant()

        self._running = True

        self._worker_thread = threading.Thread(target=self._worker, name="ant.easy")
        self._worker_thread.start()
        
        self.capabilities = self.get_capabilities()
        
        self.channels = [None]*self.capabilities["max_channels"]

    def new_channel(self, ctype, network_number=0x00, ext_assign=None):
        for i in range(len(self.channels)):
            if self.channels[i] is None:
                channel = Channel(i, self, self.ant)
                self.channels[i] = channel
                channel._assign(ctype, network_number, ext_assign)
                return channel
        _logger.debug("No free channel available")
        return None

    def remove_channel(self, channel_id):
        for i in range(len(self.channels)):
            try:
                if self.channels[i].id == channel_id:
                    self.channels[i].close()
                    self.channels[i]._unassign()
                    self.channels[i] = None
            except:
                pass

    def get_capabilities(self):
        data = self.request_message(Message.ID.RESPONSE_CAPABILITIES)
        if data[1] == Message.ID.RESPONSE_CAPABILITIES:
            #The Standard Options bit field is encoded as follows: 
            #   Bit 0 - CAPABILITIES_NO_RECEIVE_CHANNELS
            #   Bit 1 - CAPABILITIES_NO_TRANSMIT_CHANNELS
            #   Bit 2 - CAPABILITIES_NO_RECEIVE_MESSAGES
            #   Bit 3 - CAPABILITIES_NO_TRANSMIT_MESSAGES
            #   Bit 4 - CAPABILITIES_NO_ACKD_MESSAGES
            #   Bit 5 - CAPABILITIES_NO_BURST_MESSAGES
            #   Other bits are reserved
            #The Advanced Options bit field is encoded as follows: 
            #   Bit 1 - CAPABILITIES_NETWORK_ENABLED 
            #   Bit 3 - CAPABILITIES_SERIAL_NUMBER_ENABLED 
            #   Bit 4 - CAPABILITIES_PER_CHANNEL_TX_POWER_ENABLED 
            #   Bit 5 - CAPABILITIES_LOW_PRIORITY_SEARCH_ENABLED 
            #   Bit 6 - CAPABILITIES_SCRIPT_ENABLED 
            #   Bit 7 - CAPABILITIES_SEARCH_LIST_ENABLED 
            #   Other bits are reserved
            #The Advanced Options 2 bit field is encoded as follows: 
            #   Bit 0 - CAPABILITIES_LED_ENABLED 
            #   Bit 1 - CAPABILITIES_EXT_MESSAGE_ENABLED 
            #   Bit 2 - CAPABILITIES_SCAN_MODE_ENABLED 
            #   Bit 3 - Reserved 
            #   Bit 4 - CAPABILITIES_PROX_SEARCH_ENABLED 
            #   Bit 5 - CAPABILITIES_EXT_ASSIGN_ENABLED 
            #   Bit 6 - CAPABILITIES_FS_ANTFS_ENABLED 
            #   Bit 7 - CAPABILITIES_FIT1_ENABLED
            #   Other bits are reserved
            #The Advanced Options 3 bit field is encoded as follows: 
            #   Bit 0 - CAPABILITIES_ADVANCED_BURST_ENABLED
            #   Bit 1 - CAPABILITIES_EVENT_BUFFERING_ENABLED 
            #   Bit 2 - CAPABILITIES_EVENT_FILTERING_ENABLED 
            #   Bit 3 - CAPABILITIES_HIGH_DUTY_SEARCH_ENABLED 
            #   Bit 4 - CAPABILITIES_SEARCH_SHARING_ENABLED 
            #   Bit 5 - Reserved. 
            #   Bit 6 - CAPABILITIES_SELECTIVE_DATA_UPDATES_ENABLED 
            #   Bit 7 - CAPABILITIES_ENCRYPTED_CHANNEL_ENABLED
            #The Advanced Options 4 bit field is encoded as follows: 
            #   Bit 0 - CAPABILITIES_RFACTIVE_NOTIFICATION_ENABLED
            #   Other bits are reserved
            result = {
                "max_channels" : data[2][0],
                "max_networks" : data[2][1],
                "standard_options" : data[2][2],
                "advanced_options" : data[2][3],
                "advanced_options2" : data[2][4],
                "max_sensrcore_channels": data[2][5],
            }
            if len(data[2])>=7:
                result["advanced_options3"] = data[2][6]
            if len(data[2])>=8:
                result["advanced_options4"] = data[2][7]
            return result
        else:
            _logger.debug(
                "capabilities requested and not received (message id 0x{:02x} , but should be 0x{:02x})".format(data[2][4],Message.ID.RESPONSE_CAPABILITIES))
            return

    def request_message(self, messageId):
        _logger.debug("requesting message %#02x", messageId)
        self.ant.request_message(0, messageId)
        _logger.debug("done requesting message %#02x", messageId)
        return self.wait_for_special(messageId)

    def set_network_key(self, network, key):
        self.ant.set_network_key(network, key)
        return self.wait_for_response(Message.ID.SET_NETWORK_KEY)

    def wait_for_event(self, ok_codes):
        return wait_for_event(ok_codes, self._events, self._event_cond)

    def wait_for_response(self, event_id):
        return wait_for_response(event_id, self._responses, self._responses_cond)

    def wait_for_special(self, event_id):
        return wait_for_special(event_id, self._responses, self._responses_cond)

    def _worker_response(self, channel, event, data):
        self._responses_cond.acquire()
        self._responses.append((channel, event, data))
        self._responses_cond.notify()
        self._responses_cond.release()

    def _worker_event(self, channel, event, data):
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

        # TODO: check capabilities
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
            except queue.Empty as e:
                pass

    def start(self):
        self._main_thread = threading.Thread(target=self._main, name="_main")
        self._main_thread.start()

    def stop(self):
        if self._running:
            _logger.debug("Stoping ant.easy")
            self._running = False
            self.ant.stop()
            self._worker_thread.join()
            self._main_thread.join()
            self._main_thread = None
