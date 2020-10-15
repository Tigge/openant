from __future__ import absolute_import, print_function

from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.base.message import Message
from ant.antplus.controller import AntPlusController
from ant.antplus.fec import FECDevice
from ant.antplus.device import AntPlusDevice # generic antplus device, should not be used directly (??)

import logging
import struct
import threading
import sys

import time #for show_status time.sleep quick & dirty

#logging.basicConfig(filename='antplus_controller_nobgscan.log',level=logging.DEBUG)
logging.basicConfig(filename='antplus_test.log',level=logging.INFO, format='%(asctime)s %(message)s')
#not logging to file means printing to console
#logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
_logger = logging.getLogger("examples.antplus.test")

'''device_number, device_type, transmission_type, channel_period
direto : 
6574, 11, 5, 8182
6574, 17, 5, 8192
6574, 121, 1, 8086
'''

def on_new_device(channel_id):
    print(f"controller bgscan found device with channel id : {channel_id}")

def show_status (fec_device):
    while True:
        print(fec_device.status)
        print()
        time.sleep(1.0)

controller = AntPlusController()
controller.on_new_device = on_new_device

def start_scan():
    controller.start_scan()
def stop_scan():
    controller.stop_scan()

fec = None

def start_fec():
    global fec
    fec = FECDevice(controller.node, 6574, 17, 5) #device_number, device_type, transmission_type

def stop():
    if fec:
        fec.close()
    if controller:
        controller.close()

#fec.get_manufacturer_info()
# other devices TODO!
#bps = AntPlusDevice(controller.node, 6574, 11, 5, 8182) #device_number, device_type, transmission_type, channel_period
#bsc = AntPlusDevice(controller.node, 6574, 121, 1, 8086) #device_number, device_type, transmission_type, channel_period

#close:
#fec.close() # close the channel to the FE-C device
#controller.close() # closing the controller frees up the usb device (ANT-stick)
