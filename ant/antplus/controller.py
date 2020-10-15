from __future__ import absolute_import, print_function

from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.base.message import Message

import logging
import struct
import threading
import sys

import pickle # save/restore scanned devices
import array # TODO : dit kan beter!

NETWORK_KEY= [0xb9, 0xa5, 0x21, 0xfb, 0xbd, 0x72, 0xc3, 0x45]

_logger = logging.getLogger("ant.antplus.controller")

class AntPlusController():
    def __init__(self):
        self.node = Node()
        self.node.set_network_key(0x00, NETWORK_KEY) #start an ANT node with the ANT+ network key
        self.antplus_devices = []
        self.channel_bgscan = None
        # ant node in a separate thread, not to lock up the console
        self._node_thread = threading.Thread(target=self._run_node, name="ant.node")
        self._node_thread.start()

    def open(self):
        #everything is done at init
        pass

    def close(self):
        self.stop_scan() # close the bgscan channel if any
        self.node.stop() # terminate the node thread
        self._node_thread.join() # wait for termination of the node thread

    def start_scan(self):
        # TODO : optimaliseren voor background scan
        if not self.channel_bgscan :
            channel_bgscan = self.node.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE,0x00,0x01)
            channel_bgscan.on_broadcast_data = self._on_bgscan_bcdata
            channel_bgscan.on_acknowledge = self._on_bgscan_ackdata
            channel_bgscan.on_burst_data = self._on_bgscan_burstdata

            channel_bgscan.set_id(0, 0, 0) # all wild cards
            channel_bgscan.enable_extended_messages(1)
            channel_bgscan.set_search_timeout(0xFF)
            channel_bgscan.set_period(8191) #8070
            channel_bgscan.set_rf_freq(57)
            channel_bgscan.open()
            self.channel_bgscan = channel_bgscan

    def stop_scan(self):
        if self.channel_bgscan :
            self.channel_bgscan.close()
            self.channel_bgscan = None
    
    def save_devices(self, filename):
        with open(filename,'wb') as f:
            pickle.dump(self.antplus_devices, f)
    
    def restore_devices(self, filename):
        with open(filename,'rb') as f:
            self.antplus_devices = pickle.load(f)

    def get_devices (self):
        return self.antplus_devices

    # thread function for the antplus node
    def _run_node(self):
        try:
            self.node.start()
        finally:
            self.node.stop()

    def _on_bgscan_bcdata(self, data):
        _logger.info(f"bgscan:bc: {data}")
        assert len(data) > 8
        assert data[8] == 0x80 # flag byte
        #deviceNumberLSB = data[9]
        #deviceNumberMSB = data[10]
        #device_number = deviceNumberLSB + (deviceNumberMSB<<8)
        a_device = {}
        a_device["device_number"] = int.from_bytes(data[9:11],byteorder='little')
        a_device["device_type"] = data[11]
        a_device["transmission_type"] = data[12]
        _logger.info(f"Extended data: {a_device}")
        if not a_device in self.antplus_devices:
            self.antplus_devices.append(a_device)
            # optional new device found callback
            if self.on_new_device:
                self.on_new_device (a_device)

    def _on_bgscan_ackdata(self, data):
        _logger.info(f"bgscan:ack: {data}")

    def _on_bgscan_burstdata(self, data):
        _logger.info(f"bgscan:burst : {data}")
    
    # override this in application
    # controller.on_new_device = myfunc
    def on_new_device(self, device):
        _logger.info(f"on_new_device(default): {device}")



