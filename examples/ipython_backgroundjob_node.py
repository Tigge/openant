"""
Example shows how to use iPython backgroundjobs to run node runner in background whilst being able to interact with a device at the iPython prompt

Change the `device` to ones device of choice - a Dropper post here
"""
from IPython.lib import backgroundjobs as bg

from openant.devices import ANTPLUS_NETWORK_KEY
from openant.easy.node import Node
from openant.devices.dropper_seatpost import (
    DropperSeatpost,
    DropperSeatpostData,
    ValveState,
)

device = None

def node_runner(node, device):
    try:
        print(f"Starting {device}, press Ctrl-C to finish")
        node.start()
    except KeyboardInterrupt:
        print(f"Closing ANT+ device...")
    finally:
        device.close_channel()
        node.stop()

def on_found():
    print(f"Device {device} found and receiving")

def on_device_data(page: int, page_name: str, data):
    if isinstance(data, DropperSeatpostData):
        print(f"Dropper seatpost state: {data.valve_state}")

node = Node()
node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

device = DropperSeatpost(node, device_id=0)

device.on_found = on_found
device.on_device_data = on_device_data

jobs = bg.BackgroundJobManager()
jobs.new(node_runner, node, device)
